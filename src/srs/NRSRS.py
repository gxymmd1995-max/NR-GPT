"""SRS，固定 TS 38.211 V15.2.0 §5.2、§6.4.1.4；RRC 范围见 38.331 V15.2.1。

坐标使用 NRGrid 的 [局部端口, 时隙内符号, 载波内子载波]，从零开始。
仅合成当前时隙的参考信号；调度许可、TDD 方向和功控由调用者提供。
"""

from dataclasses import dataclass, fields
from math import isqrt, prod
from typing import ClassVar

import numpy as np

from cell import NRCell
from common import NRCommon
from grid import NRGrid
from srs._tables import BANDWIDTH_TABLE, PHI_12, PHI_24


def _integer(name: str, value: int, lower: int, upper: int) -> None:
    """验证 Python int 闭区间，明确拒绝 bool、NumPy 整数和浮点数。"""
    if type(value) is not int:
        raise TypeError(f"{name} must be a Python int, not bool")
    if not lower <= value <= upper:
        raise ValueError(f"{name} must be in [{lower}, {upper}]")


def _base_sequence(length: int, u: int, v: int) -> np.ndarray:
    """§5.2.2.1/2：SRS 所需的 12/24 点相位表或 >=36 点 Zadoff-Chu 扩展。"""
    if length in (12, 24):
        phases = (PHI_12 if length == 12 else PHI_24)[u]
        return np.exp(1j * np.pi / 4 * np.asarray(phases))
    # 最大严格小于 M 的质数 N_ZC；SRS 的 m 为 4 的倍数，不会产生 6/18/30 点。
    prime = length - 1
    while any(prime % divisor == 0 for divisor in range(2, isqrt(prime) + 1)):
        prime -= 1
    q_bar = prime * (u + 1) / 31
    q = int(np.floor(q_bar + 0.5)) + v * (-1) ** int(np.floor(2 * q_bar))
    m = np.arange(length, dtype=np.int64) % prime
    # 相位模 2π 后取指数可降低大带宽时的浮点误差；与原公式代数等价。
    phase = (q * m * (m + 1)) % (2 * prime)
    return np.exp(-1j * np.pi * phase / prime)


@dataclass(frozen=True, slots=True)
class NRSRS:
    """不可变的单个 SRS resource；generate 给出序列，map_to_grid 执行端口归一化。

    frequency_shift 为载波内 RB 偏移，显式检查实际分配落在 cell 活动 BWP。
    enabled 是外部调度许可：非周期资源须由调用者在已触发的目标时隙开启；
    半持续资源须由调用者反映激活状态。此类不解码 DCI/MAC，不推断 TDD 方向。
    """

    cell: NRCell
    n_ports: int = 1                 # 协议端口 1000..；不等于物理天线数。
    n_symbols: int = 1               # 连续 OFDM 符号数 1/2/4。
    start_position: int = 0          # 从时隙末端倒数的 l_offset，0..5。
    c_srs: int = 0                   # 带宽配置表的行 0..63。
    b_srs: int = 0                   # 带宽配置表的层级 0..3。
    b_hop: int = 0                   # 小于 b_srs 时开启频率跳频。
    k_tc: int = 2                    # 梳齿间隔，单位：子载波，2/4。
    comb_offset: int = 0             # 梳齿内偏移，0..k_tc-1。
    cyclic_shift: int = 0            # 基础循环移位编号，comb2:0..7；comb4:0..11。
    frequency_shift: int = 0         # n_shift，载波内 RB 单位，R15 范围 0..268。
    frequency_position: int = 0      # n_RRC，0..67，以 4RB 为基本位置步进。
    sequence_id: int = 0             # 10 bit R15 sequenceId，独立于 PCI。
    group_seq_hopping: str = "neither"
    repetition: int = 1              # 同一频率位置上的符号重复数 1/2/4。
    resource_type: str = "periodic"
    periodicity: int = 1             # 时隙单位，固定 R15 的 17 种取值。
    slot_offset: int = 0             # 周期内时隙偏移。
    enabled: bool = True             # 软件调度许可，不是 RRC 原始字段。

    SPEC_BASELINE: ClassVar[str] = "TS 38.211 V15.2.0; TS 38.331 V15.2.1"
    PERIODICITIES: ClassVar[tuple[int, ...]] = (1, 2, 4, 5, 8, 10, 16, 20, 32, 40, 64, 80,
                                               160, 320, 640, 1280, 2560)

    def __post_init__(self) -> None:
        """校验固定 R15 范围及联合约束；实际频域越界在 indices/map 时检查。"""
        if not isinstance(self.cell, NRCell):
            raise TypeError("cell must be an NRCell instance")
        for name, lower, upper in (("n_ports", 1, 4), ("n_symbols", 1, 4),
                                   ("start_position", 0, 5), ("c_srs", 0, 63),
                                   ("b_srs", 0, 3), ("b_hop", 0, 3), ("k_tc", 2, 4),
                                   ("frequency_shift", 0, 268), ("frequency_position", 0, 67),
                                   ("sequence_id", 0, 1023), ("repetition", 1, 4),
                                   ("periodicity", 1, 2560)):
            _integer(name, getattr(self, name), lower, upper)
        for name in ("n_ports", "n_symbols", "repetition"):
            if getattr(self, name) not in (1, 2, 4):
                raise ValueError(f"R15 {name} must be 1, 2 or 4")
        if self.k_tc not in (2, 4):
            raise ValueError("R15 k_tc must be 2 or 4")
        _integer("comb_offset", self.comb_offset, 0, self.k_tc - 1)
        _integer("cyclic_shift", self.cyclic_shift, 0, self.max_cyclic_shifts - 1)
        if self.start_position < self.n_symbols - 1:
            raise ValueError("start_position must be >= n_symbols - 1")
        if self.repetition > self.n_symbols:
            raise ValueError("repetition must be <= n_symbols")
        if self.periodicity not in self.PERIODICITIES:
            raise ValueError("periodicity is outside the fixed R15 set")
        _integer("slot_offset", self.slot_offset, 0, self.periodicity - 1)
        for name, allowed in (("group_seq_hopping", ("neither", "groupHopping", "sequenceHopping")),
                              ("resource_type", ("periodic", "semi-persistent", "aperiodic"))):
            if not isinstance(getattr(self, name), str):
                raise TypeError(f"{name} must be a str")
            if getattr(self, name) not in allowed:
                raise ValueError(f"{name} must be one of {allowed}")
        if self.resource_type == "aperiodic" and (self.periodicity, self.slot_offset) != (1, 0):
            raise ValueError("aperiodic uses enabled as trigger permission; periodicity/offset must be 1/0")
        if type(self.enabled) is not bool:
            raise TypeError("enabled must be a bool")

    @property
    def symbol_start(self) -> int:
        """l0，时隙内零起始符号；§6.4.1.4.1，兼容普通/扩展 CP。"""
        return self.cell.symbols_per_slot - 1 - self.start_position

    @property
    def bandwidth_rb(self) -> int:
        """当前传输带宽 m_b，单位 RB；表 6.4.1.4.3-1。"""
        return BANDWIDTH_TABLE[self.c_srs][2 * self.b_srs]

    @property
    def sequence_length(self) -> int:
        """每端口每 OFDM 符号 M=m_b*12/K_TC 个复数；§6.4.1.4.3。"""
        return self.bandwidth_rb * 12 // self.k_tc

    @property
    def max_cyclic_shifts(self) -> int:
        """n_cs,max，comb2 为 8、comb4 为 12；§6.4.1.4.2。"""
        return 8 if self.k_tc == 2 else 12

    @property
    def antenna_ports(self) -> tuple[int, ...]:
        """协议逻辑端口号 1000+i；NRGrid 轴使用本地 i。"""
        return tuple(range(1000, 1000 + self.n_ports))

    @property
    def absolute_slot(self) -> int:
        """当前 SFN 周期内槽号 n_f*N_slots/frame+n_slot；不累计 SFN 回绕。"""
        return self.cell.n_frame * self.cell.slots_per_frame + self.cell.n_slot

    @property
    def is_candidate_slot(self) -> bool:
        """§6.4.1.4.4 的候选时隙；不表示已获得 TDD/触发/激活许可。"""
        return self.resource_type == "aperiodic" or (self.absolute_slot - self.slot_offset) % self.periodicity == 0

    @property
    def is_active(self) -> bool:
        """候选时隙与外部 enabled 同时满足；未获许可时返回空序列/索引。"""
        return self.enabled and self.is_candidate_slot

    def _frequency_indices(self) -> tuple[np.ndarray, np.ndarray]:
        """§6.4.1.4.3：计算 n_b[B+1,L] 和载波内 k0[P,L]（不应用时隙许可）。"""
        table = BANDWIDTH_TABLE[self.c_srs]
        ms = table[0::2]
        ns = table[1::2]
        nb = np.zeros((self.b_srs + 1, self.n_symbols), dtype=np.int64)
        for l_prime in range(self.n_symbols):
            counter = l_prime // self.repetition
            if self.resource_type != "aperiodic":
                counter += ((self.absolute_slot - self.slot_offset) // self.periodicity
                            * (self.n_symbols // self.repetition))
            for b in range(self.b_srs + 1):
                position = 4 * self.frequency_position // ms[b]
                if self.b_hop < b:
                    # N_bhop 在 F_b 的连乘中强制为 1；在原始 n_b 的模中仍用表值。
                    prior = prod(ns[self.b_hop + 1:b])
                    if ns[b] % 2 == 0:
                        quotient = (counter % (prior * ns[b])) // prior
                        hopping = ns[b] // 2 * quotient + quotient // 2
                    else:
                        hopping = ns[b] // 2 * (counter // prior)
                    position += hopping
                nb[b, l_prime] = position % ns[b]
        comb = np.full(self.n_ports, self.comb_offset, dtype=np.int64)
        if self.n_ports == 4 and self.cyclic_shift >= self.max_cyclic_shifts // 2:
            comb[1::2] = (self.comb_offset + self.k_tc // 2) % self.k_tc
        k0 = (12 * self.frequency_shift + comb[:, None]
              + np.sum(12 * np.asarray(ms[:self.b_srs + 1])[:, None] * nb, axis=0))
        return nb, k0

    def indices(self) -> np.ndarray:
        """返回 N×3 int64 [p,l,k]；顺序端口→符号→序列点，未激活为 (0,3)。

        每个实际分配 RE 必须落在活动 BWP，越界整体报错，不裁剪也不回绕。
        """
        if not self.is_active:
            return np.empty((0, 3), dtype=np.int64)
        _, k0 = self._frequency_indices()
        count = self.sequence_length
        k = k0[:, :, None] + self.k_tc * np.arange(count)
        low = 12 * (self.cell.bwp_start - self.cell.n_start_grid)
        high = low + 12 * self.cell.bwp_size
        if np.any(k < low) or np.any(k >= high):
            raise ValueError("SRS allocation is outside the active BWP; check frequency_shift and hopping bandwidth")
        ports = np.broadcast_to(np.arange(self.n_ports)[:, None, None], k.shape)
        symbols = np.broadcast_to((self.symbol_start + np.arange(self.n_symbols))[None, :, None], k.shape)
        return np.stack((ports, symbols, k), axis=-1).reshape(-1, 3)

    def sequence_parameters(self) -> dict[str, np.ndarray]:
        """§6.4.1.4.2：返回每符号 u/v 与每端口 alpha(rad) 的新数组。

        不应用 enabled/候选时隙，仅用于观察配置的序列参数。
        PRBS 每帧重新初始化，索引使用帧内 n_slot 而非 absolute_slot。
        """
        params = NRCommon.srs_sequence_uv(
            self.sequence_id, self.cell.n_slot, self.symbol_start, self.n_symbols,
            self.sequence_length, self.group_seq_hopping, self.cell.symbols_per_slot)
        shifts = (self.cyclic_shift + self.max_cyclic_shifts * np.arange(self.n_ports) // self.n_ports)
        alpha = 2 * np.pi * (shifts % self.max_cyclic_shifts) / self.max_cyclic_shifts
        return {**params, "alpha": alpha}

    def generate(self) -> np.ndarray:
        """返回 [M*n_symbols, n_ports] complex128 原始单位模序列，对齐 MATLAB nrSRS。

        不含 beta 或 1/sqrt(n_ports)；未激活返回 (0,n_ports)。先验证实际 BWP 边界。
        """
        self.indices()
        if not self.is_active:
            return np.empty((0, self.n_ports), dtype=np.complex128)
        params = self.sequence_parameters()
        n = np.arange(self.sequence_length)
        rotation = np.exp(1j * n[:, None] * params["alpha"])
        return np.concatenate([_base_sequence(self.sequence_length, int(u), int(v))[:, None] * rotation
                               for u, v in zip(params["u"], params["v"])], axis=0)

    def map_to_grid(self, grid: NRGrid, beta: float = 1.0, owner: str = "SRS",
                    overwrite: bool = False) -> int:
        """§6.4.1.4.3：写 beta/sqrt(P)*r，使用 NRGrid 原子冲突检查；返回 RE 数。

        beta 是调用者给定的非负有限线性幅度，不是 dB；不实现闭环功控。
        网格必须绑定相同 NRCell 值，至少有 n_ports 个局部端口；使用前 P 个。
        """
        if not isinstance(grid, NRGrid):
            raise TypeError("grid must be an NRGrid instance")
        if grid.cell != self.cell or grid.n_ports < self.n_ports:
            raise ValueError("grid must have the same NRCell and enough logical ports")
        if isinstance(beta, bool) or not isinstance(beta, (int, float)):
            raise TypeError("beta must be a real number, not bool")
        if not np.isfinite(beta) or beta < 0:
            raise ValueError("beta must be finite and >= 0")
        values = self.generate().ravel(order="F") * (beta / np.sqrt(self.n_ports))
        return grid.map(self.indices(), values, owner, overwrite=overwrite)

    def to_dict(self) -> dict[str, object]:
        """返回可 JSON 编码的完整输入快照；cell 使用其 to_dict，保留 enabled。"""
        return {field.name: self.cell.to_dict() if field.name == "cell" else getattr(self, field.name)
                for field in fields(self)}

    def to_matlab_config(self) -> dict[str, object]:
        """返回 nrSRSConfig 的固定 R15 字段；carrier 用 cell.to_matlab_config 单独建立。

        关闭定位、部分频域探测、8 端口、comb/cyclic-shift 跳变等后续扩展。
        carrier 直接使用 cell.to_matlab_config 的 NFrame 与帧内 NSlot；
        不要同时把 NSlot 换成 absolute_slot，否则 MATLAB 将重复累计帧号。
        """
        return {"NumSRSPorts": self.n_ports, "NumSRSSymbols": self.n_symbols,
                "SymbolStart": self.symbol_start, "CSRS": self.c_srs, "BSRS": self.b_srs,
                "BHop": self.b_hop, "KTC": self.k_tc, "KBarTC": self.comb_offset,
                "CyclicShift": self.cyclic_shift, "FrequencyStart": self.frequency_shift,
                "NRRC": self.frequency_position, "NSRSID": self.sequence_id,
                "GroupSeqHopping": self.group_seq_hopping, "Repetition": self.repetition,
                "ResourceType": self.resource_type,
                "SRSPeriod": ([self.periodicity, self.slot_offset] if self.resource_type != "aperiodic" else "on")
                if self.enabled else "off",
                "SRSPositioning": False, "FrequencyScalingFactor": 1, "StartRBIndex": 0,
                "EnableStartRBHopping": False, "EnableEightPortTDM": False,
                "CyclicShiftHopping": False, "CombOffsetHopping": False,
                "HoppingFinerGranularity": False, "HoppingWithRepetition": False}
