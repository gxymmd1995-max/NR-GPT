"""R15 PUSCH码本及基于互信息的RI/TPMI选择；§6.3.1.5，禁用变换预编码。"""

import numpy as np

from common.NRCommon import _integer
from common._uplink_tables import UPLINK_CODEBOOKS


class NRUplinkCodebook:
    """标准矩阵与接收机选择策略分开；只支持R15的1/2/4端口。"""

    NOISE_FLOOR = 1e-12  # 选择算法的数值下限，归一化复功率/RE；不是协议常量。

    @staticmethod
    def matrix(n_ports: int, rank: int, tpmi: int) -> np.ndarray:
        """返回[端口,层] complex128标准矩阵副本；不额外改变原表归一化。"""
        _integer("n_ports", n_ports, 1, 4)
        _integer("rank", rank, 1, n_ports)
        if n_ports not in (1, 2, 4):
            raise ValueError("R15 n_ports must be 1, 2 or 4")
        entries = UPLINK_CODEBOOKS[n_ports, rank]
        _integer("tpmi", tpmi, 0, len(entries) - 1)
        denominator_squared, rows = entries[tpmi]
        return np.asarray(rows, dtype=np.complex128) / np.sqrt(denominator_squared)

    @staticmethod
    def select(
        channel: np.ndarray,
        noise_power: float,
        tx_power: float = 1.0,
        max_rank: int | None = None,
        allowed_tpmi: dict[int, list[int]] | None = None,
    ) -> dict:
        """在共同观测频点的H[F,Rx,Tx]上搜索RI/TPMI，最大化平均log2det。

        比较时W除以其Frobenius范数，使候选使用相同UE总发送功率tx_power。
        返回的precoder仍是原表W；评分归一化约定单独给出。noise为每Rx复噪声功率。
        allowed_tpmi=None搜索全码本，否则只搜索指定rank/TPMI（外部能力/配置限制）。
        平分时确定性选择较低RI/TPMI；零信道返回None建议。不是标准强制反馈算法。
        """
        h = np.asarray(channel, dtype=np.complex128)
        if (
            h.ndim != 3
            or not all(h.shape)
            or h.shape[2] not in (1, 2, 4)
            or not np.all(np.isfinite(h))
        ):
            raise ValueError(
                "channel must be finite nonempty [frequency,rx,tx], tx=1/2/4"
            )
        for name, value in (("noise_power", noise_power), ("tx_power", tx_power)):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be a real number")
            if not np.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and >=0")
        limit = min(h.shape[1:])
        if max_rank is not None:
            _integer("max_rank", max_rank, 1, h.shape[2])
            limit = min(limit, max_rank)
        if allowed_tpmi is not None:
            if not isinstance(allowed_tpmi, dict) or not allowed_tpmi:
                raise ValueError("allowed_tpmi must be a nonempty rank->TPMI-list dict")
            for rank, entries in allowed_tpmi.items():
                _integer("allowed rank", rank, 1, limit)
                if not isinstance(entries, (list, tuple)) or not entries:
                    raise ValueError("allowed TPMI entries must be nonempty lists")
                for tpmi in entries:
                    NRUplinkCodebook.matrix(h.shape[2], rank, tpmi)
                if len(set(entries)) != len(entries):
                    raise ValueError("allowed TPMI lists must not repeat indices")
        candidates = []
        rho = tx_power / max(noise_power, NRUplinkCodebook.NOISE_FLOOR)
        for rank in range(1, limit + 1):
            entries = (
                range(len(UPLINK_CODEBOOKS[h.shape[2], rank]))
                if allowed_tpmi is None
                else sorted(allowed_tpmi.get(rank, []))
            )
            for tpmi in entries:
                w = NRUplinkCodebook.matrix(h.shape[2], rank, tpmi)
                effective = h @ (w / np.linalg.norm(w))
                eigenvalues = np.linalg.eigvalsh(
                    effective.conj().transpose(0, 2, 1) @ effective
                )
                score = float(
                    np.mean(
                        np.sum(
                            np.log1p(rho * np.maximum(eigenvalues, 0)) / np.log(2),
                            axis=1,
                        )
                    )
                )
                candidates.append({"ri": rank, "tpmi": tpmi, "score_bps_hz": score})
        best = candidates[0]
        for candidate in candidates[1:]:
            if candidate["score_bps_hz"] > best["score_bps_hz"] + 1e-10:
                best = candidate
        present = bool(np.any(h)) and tx_power > 0
        return {
            "ri": best["ri"] if present else None,
            "tpmi": best["tpmi"] if present else None,
            "precoder": (
                NRUplinkCodebook.matrix(h.shape[2], best["ri"], best["tpmi"])
                if present
                else None
            ),
            "score_bps_hz": best["score_bps_hz"],
            "candidates": candidates,
            "scoring_normalization": "W / FrobeniusNorm(W); fixed total UE tx_power",
            "noise_power_used": max(noise_power, NRUplinkCodebook.NOISE_FLOOR),
        }
