"""R15 SRS频域接收机：联合有限冲激响应LS、噪声、用户时延与上行RI/TPMI。

序列/码本来自固定R15；信道估计和指标算法是项目接收机设计，见同级文档。
输入轴[Rx,slot symbol,carrier subcarrier]，已完成OFDM与粗同步。
"""

from dataclasses import dataclass

import numpy as np

from cell import NRCell
from common import NRUplinkCodebook
from common.NRCommon import _integer
from grid import NRGrid
from srs.NRSRS import NRSRS


@dataclass(frozen=True, slots=True)
class NRSRSReceiver:
    """同一时隙的多用户联合LS接收机；块内信道假定时不变且延迟在给定窗口内。"""

    cell: NRCell
    n_delay_taps: int = 8  # 因果FIR样点数，支持延迟0..D-1；必须不超过最短CP。
    max_condition_number: float = 1e8  # 无量纲；超过上限拒绝不可可靠分离的用户/端口。
    min_snr_db: float = 0.0  # 用户信号检测的工程门限，非协议强制门限。
    first_path_relative_power: float = 0.1  # 首径判定的相对峰值功率门限，(0,1]。

    def __post_init__(self) -> None:
        """校验小区、延迟窗口和有限数值参数。"""
        if not isinstance(self.cell, NRCell):
            raise TypeError("cell must be an NRCell")
        _integer(
            "n_delay_taps", self.n_delay_taps, 1, min(self.cell.slot_cp_lengths_samples)
        )
        for name in ("max_condition_number", "min_snr_db", "first_path_relative_power"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be a real number")
            if not np.isfinite(value):
                raise ValueError(f"{name} must be finite")
        if self.max_condition_number < 1:
            raise ValueError("max_condition_number must be >=1")
        if not 0 < self.first_path_relative_power <= 1:
            raise ValueError("first_path_relative_power must be in (0,1]")

    def _references(self, resources: dict[str, NRSRS], betas: dict[str, float]) -> dict:
        """构建每用户NRGrid参考[符号,k,port]；用户之间可重叠，分离性由联合矩阵验证。"""
        if not isinstance(resources, dict) or not resources:
            raise ValueError("resources must be a nonempty user_id->NRSRS dict")
        if not isinstance(betas, dict) or any(uid not in resources for uid in betas):
            raise ValueError(
                "betas must map configured user IDs to positive amplitudes"
            )
        references = {}
        for uid, resource in resources.items():
            if not isinstance(uid, str) or not uid.strip():
                raise ValueError("user IDs must be nonblank strings")
            if not isinstance(resource, NRSRS) or resource.cell != self.cell:
                raise ValueError("each resource must be NRSRS with the receiver NRCell")
            beta = betas.get(uid, 1.0)
            if isinstance(beta, bool) or not isinstance(beta, (int, float)):
                raise TypeError("SRS beta must be a real amplitude")
            if not np.isfinite(beta) or beta <= 0:
                raise ValueError(
                    "SRS beta must be finite and >0 for channel estimation"
                )
            grid = NRGrid(self.cell, resource.n_ports)
            resource.map_to_grid(grid, beta=beta)
            references[uid] = grid.data.transpose(1, 2, 0)
        return references

    def _noise(
        self,
        rx: np.ndarray,
        observed: np.ndarray,
        residual: np.ndarray,
        leverage: np.ndarray,
        noise_mask: np.ndarray | None,
    ) -> dict:
        """每Rx/PRB复噪声功率；显式静默RE优先，否则以LS残差/自由度估计。"""
        l_count, k_count = rx.shape[1:]
        bwp_mask = np.zeros((l_count, k_count), dtype=bool)
        low = (self.cell.bwp_start - self.cell.n_start_grid) * 12
        bwp_mask[:, low : low + self.cell.bwp_size * 12] = True
        if noise_mask is not None:
            mask = np.asarray(noise_mask)
            if mask.shape != (l_count, k_count) or mask.dtype.kind != "b":
                raise ValueError("noise_mask must be boolean [symbol,subcarrier]")
            if not np.any(mask) or np.any(mask & observed) or np.any(mask & ~bwp_mask):
                raise ValueError(
                    "noise_mask must contain known muted REs inside BWP, outside all SRS"
                )
            powers = np.abs(rx[:, mask]) ** 2
            frequencies = np.nonzero(mask)[1]
            dof = np.ones(len(frequencies))
            method = "muted_re"
        else:
            frequencies = np.nonzero(observed)[1]
            powers = np.abs(residual.T) ** 2
            dof = np.maximum(1 - leverage, 0)
            if dof.sum() <= 1e-8:
                raise ValueError(
                    "no residual noise degrees of freedom; supply explicit muted noise_mask"
                )
            method = "ls_residual"
        wide = powers.sum(axis=1) / dof.sum()
        narrow = np.full((rx.shape[0], self.cell.n_size_grid), np.nan)
        counts = np.zeros(self.cell.n_size_grid, dtype=np.int64)
        effective_dof = np.zeros(self.cell.n_size_grid)
        for rb in range(self.cell.n_size_grid):
            selected = frequencies // 12 == rb
            counts[rb] = int(selected.sum())
            effective_dof[rb] = dof[selected].sum()
            if effective_dof[rb] > 1e-8:
                narrow[:, rb] = powers[:, selected].sum(axis=1) / effective_dof[rb]
        return {
            "method": method,
            "units": "normalized complex power per RE per receive branch",
            "wideband_noise_power": float(wide.mean()),
            "wideband_noise_power_per_rx": wide,
            "narrowband_noise_power": narrow.mean(axis=0),
            "narrowband_noise_power_per_rx": narrow,
            "narrowband_re_count": counts,
            "narrowband_degrees_of_freedom": effective_dof,
        }

    def estimate(
        self,
        rx_grid: np.ndarray,
        resources: dict[str, NRSRS],
        *,
        noise_mask: np.ndarray | None = None,
        betas: dict[str, float] | None = None,
        selection_options: dict[str, dict] | None = None,
    ) -> dict:
        """联合估计所有已知用户；返回噪声、每用户CIR/H/时延/SNR/RI/TPMI。

        rx_grid=[cell.n_rx_antennas,cell.symbols_per_slot,cell.n_subcarriers]，归一化复幅度。
        noise_mask由调用者指定确知静默的RE，不能仅因不属于某用户便认定为空。
        betas须匹配发送端已知幅度。selection_options按用户传入码本select的tx_power、
        max_rank、allowed_tpmi；该选项影响推荐，不改变SRS信道估计。
        """
        rx = np.asarray(rx_grid, dtype=np.complex128)
        expected = (
            self.cell.n_rx_antennas,
            self.cell.symbols_per_slot,
            self.cell.n_subcarriers,
        )
        if rx.shape != expected or not np.all(np.isfinite(rx)):
            raise ValueError(f"rx_grid must be finite with shape {expected}")
        references = self._references(resources, {} if betas is None else betas)
        options = {} if selection_options is None else selection_options
        if not isinstance(options, dict):
            raise TypeError("selection_options must be a dict")
        for uid, entry in options.items():
            if (
                uid not in resources
                or not isinstance(entry, dict)
                or set(entry) - {"tx_power", "max_rank", "allowed_tpmi"}
            ):
                raise ValueError(
                    "selection_options must contain configured users and valid selector options"
                )
        active = {
            uid: ref for uid, ref in references.items() if resources[uid].is_active
        }
        observed = np.zeros(rx.shape[1:], dtype=bool)
        for ref in active.values():
            observed |= np.any(ref != 0, axis=2)
        coordinates = np.argwhere(observed)  # [slot symbol,k]，symbol优先，频率递增。
        frequencies = coordinates[:, 1]
        basis = np.exp(
            -2j
            * np.pi
            * frequencies[:, None]
            * np.arange(self.n_delay_taps)
            / self.cell.n_fft
        )
        blocks, spans = [], {}
        column = 0
        for uid, ref in active.items():
            # 每用户按port->delay tap排序；时隙内所有SRS符号共享同一FIR。
            x = ref[observed]
            block = (x[:, :, None] * basis[:, None, :]).reshape(len(coordinates), -1)
            spans[uid] = slice(column, column + block.shape[1])
            column += block.shape[1]
            blocks.append(block)
        a = (
            np.concatenate(blocks, axis=1)
            if blocks
            else np.empty((0, 0), dtype=complex)
        )
        y = rx[:, observed].T
        condition = None
        if column:
            u, singular, vh = np.linalg.svd(a, full_matrices=False)
            rank = int(
                np.count_nonzero(
                    singular > singular[0] * max(a.shape) * np.finfo(float).eps
                )
            )
            condition = (
                float(singular[0] / singular[-1]) if singular[-1] > 0 else float("inf")
            )
            if rank < column or condition > self.max_condition_number:
                raise ValueError(
                    "SRS users/ports/delay taps are not identifiable or design matrix is ill-conditioned"
                )
            inverse = (vh.conj().T / singular) @ u.conj().T
            coefficients = inverse @ y
            residual = y - a @ coefficients
            leverage = np.sum(np.abs(u) ** 2, axis=1)
        else:
            inverse = np.empty((0, 0), dtype=complex)
            coefficients = np.empty((0, rx.shape[0]), dtype=complex)
            residual = y
            leverage = np.empty(0)
        noise = self._noise(rx, observed, residual, leverage, noise_mask)
        noise_power = noise["wideband_noise_power"]
        transform = np.exp(
            -2j
            * np.pi
            * np.arange(self.cell.n_subcarriers)[:, None]
            * np.arange(self.n_delay_taps)
            / self.cell.n_fft
        )
        users = {}
        for uid, resource in resources.items():
            if uid not in active:
                users[uid] = {
                    "status": "inactive",
                    "ri": None,
                    "tpmi": None,
                    "delay_samples": None,
                    "snr_db": None,
                    "rssi": None,
                    "rssi_db": None,
                    "rsrp": None,
                    "rsrp_db": None,
                }
                continue
            span = spans[uid]
            cir = (
                coefficients[span]
                .reshape(resource.n_ports, self.n_delay_taps, rx.shape[0])
                .transpose(2, 0, 1)
            )
            channel = np.einsum("rpd,kd->rpk", cir, transform)
            # 去除有限LS模型拟合噪声造成的信号功率正偏；白噪声近似使用宽带噪声均值。
            user_rows = np.any(active[uid][observed] != 0, axis=1)
            prediction = a[user_rows, span] @ coefficients[span]
            noise_gain = np.mean(
                np.sum(np.abs(a[user_rows, span] @ inverse[span]) ** 2, axis=1)
            )
            # RSRP：用户重构信号在其实际SRS RE上的去噪平均功率；接收支路取平均。
            rsrp_per_rx = np.maximum(
                np.mean(np.abs(prediction) ** 2, axis=0)
                - noise["wideband_noise_power_per_rx"] * noise_gain,
                0,
            )
            signal_power = float(rsrp_per_rx.mean())
            # RSSI：每个SRS符号内首末SRS RE之间全部子载波总接收功率（含干扰/噪声）。
            # 每符号单独取带宽边界，适用于跳频；跨SRS符号和Rx取平均，不除以带宽。
            own_mask = np.any(active[uid] != 0, axis=2)
            symbol_powers = []
            bandwidths = []
            for symbol in np.flatnonzero(np.any(own_mask, axis=1)):
                ks = np.flatnonzero(own_mask[symbol])
                symbol_powers.append(
                    np.sum(np.abs(rx[:, symbol, ks[0] : ks[-1] + 1]) ** 2, axis=1)
                )
                bandwidths.append(int(ks[-1] - ks[0] + 1))
            rssi_per_rx = np.mean(symbol_powers, axis=0)
            rssi = float(rssi_per_rx.mean())
            ratio = signal_power / max(noise_power, NRUplinkCodebook.NOISE_FLOOR)
            snr_db = float(10 * np.log10(ratio)) if ratio > 0 else None
            detected = snr_db is not None and snr_db >= self.min_snr_db
            sounding_mask = np.any(np.any(active[uid] != 0, axis=2), axis=0)
            choice = NRUplinkCodebook.select(
                channel[:, :, sounding_mask].transpose(2, 0, 1),
                float(noise_power),
                **options.get(uid, {}),
            )
            # 每tap系数的白噪声方差 = sigma² * ||伪逆对应行||²。
            coefficient_noise = noise_power * np.sum(
                np.abs(inverse[span]) ** 2, axis=1
            ).reshape(resource.n_ports, self.n_delay_taps)
            delay_power = np.maximum(
                np.sum(np.abs(cir) ** 2, axis=(0, 1))
                - rx.shape[0] * coefficient_noise.sum(axis=0),
                0,
            )
            mass = float(delay_power.sum())
            peak = int(np.argmax(delay_power)) if detected and mass > 0 else None
            first = (
                int(
                    np.flatnonzero(
                        delay_power
                        >= delay_power.max() * self.first_path_relative_power
                    )[0]
                )
                if peak is not None
                else None
            )
            mean = (
                float(delay_power @ np.arange(self.n_delay_taps) / mass)
                if peak is not None
                else None
            )
            rms = (
                float(
                    np.sqrt(
                        delay_power @ (np.arange(self.n_delay_taps) - mean) ** 2 / mass
                    )
                )
                if mean is not None
                else None
            )
            users[uid] = {
                "status": "detected" if detected else "below_threshold",
                "cir": cir,
                "channel": channel,
                "channel_observed_mask": sounding_mask,
                "delay_power": delay_power,
                "signal_power": signal_power,
                "snr_db": snr_db,
                "rsrp": signal_power,
                "rsrp_db": (
                    float(10 * np.log10(signal_power)) if signal_power > 0 else None
                ),
                "rsrp_per_rx": rsrp_per_rx,
                "rssi": rssi,
                "rssi_db": float(10 * np.log10(rssi)) if rssi > 0 else None,
                "rssi_per_rx": rssi_per_rx,
                "rssi_bandwidth_subcarriers": bandwidths,
                "measurement_units": "normalized linear power; dB relative to unit power, not dBm",
                "delay_samples": peak,
                "delay_s": (
                    peak / self.cell.sample_rate_hz if peak is not None else None
                ),
                "delay_tc": (
                    peak * self.cell.tc_per_sample if peak is not None else None
                ),
                "first_path_delay_samples": first,
                "first_path_delay_s": (
                    first / self.cell.sample_rate_hz if first is not None else None
                ),
                "delay_window_edge": (
                    peak in (0, self.n_delay_taps - 1) if peak is not None else None
                ),
                "mean_delay_samples": mean,
                "rms_delay_spread_samples": rms,
                "ri": choice["ri"] if detected else None,
                "tpmi": choice["tpmi"] if detected else None,
                "selection": choice if detected else None,
            }
        return {
            "noise": noise,
            "users": users,
            "design_condition_number": condition,
            "observation_count": len(coordinates),
            "unknown_count": column,
            "residual_power": (
                float(np.mean(np.abs(residual) ** 2)) if residual.size else None
            ),
            "delay_resolution_s": 1 / self.cell.sample_rate_hz,
            "delay_window_s": (self.n_delay_taps - 1) / self.cell.sample_rate_hz,
        }
