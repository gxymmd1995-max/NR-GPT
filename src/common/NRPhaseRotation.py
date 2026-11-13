"""NR逐OFDM符号相位补偿及FFT窗口/定时相位因子；TS38.211 V15.2.0 §5.3.1/5.4。"""

from dataclasses import dataclass

import numpy as np

from cell import NRCell
from common.NRCommon import _integer
from common._validation import real_value


@dataclass(frozen=True, slots=True)
class NRPhaseRotation:
    """单numerology载波；逐符号相位原点在子帧首，CFO的连续时间原点另由channel管理。"""

    cell: NRCell
    carrier_frequency_hz: float = 0.0  # f0，Hz；0表示不施加射频载波对应的符号相位补偿。

    def __post_init__(self):
        """验证小区和非负有限载频。"""
        if not isinstance(self.cell, NRCell):
            raise TypeError("cell must be an NRCell")
        real_value("carrier_frequency_hz", self.carrier_frequency_hz, 0)

    def symbol_phases(self) -> np.ndarray:
        """返回当前slot每符号发送补偿角（rad，未wrap）；§5.4，CP与有效部分用同一角。"""
        useful_starts = [
            self.cell.symbol_timing(l)["start_sample_in_subframe"] + cp
            for l, cp in enumerate(self.cell.slot_cp_lengths_samples)
        ]
        return (
            -2
            * np.pi
            * self.carrier_frequency_hz
            * np.asarray(useful_starts)
            / self.cell.sample_rate_hz
        )

    def symbol_phasors(self, inverse: bool = False) -> np.ndarray:
        """单位复数[L]；发送exp(j*phase)，接收inverse=True使用共轭。"""
        if type(inverse) is not bool:
            raise TypeError("inverse must be bool")
        return np.exp(((-1j) if inverse else 1j) * self.symbol_phases())

    def apply_grid(self, grid: np.ndarray, inverse: bool = False) -> np.ndarray:
        """对[P,L,K]复数网格逐符号旋转，返回新数组；不改变NRGrid标签。"""
        values = np.asarray(grid, dtype=np.complex128)
        if (
            values.ndim != 3
            or values.shape[0] < 1
            or values.shape[1:] != (self.cell.symbols_per_slot, self.cell.n_subcarriers)
            or not np.all(np.isfinite(values))
        ):
            raise ValueError(
                "grid must be finite [branch,slot symbol,carrier subcarrier]"
            )
        return values * self.symbol_phasors(inverse)[None, :, None]

    def timing_phasors(self, delay_samples: float) -> np.ndarray:
        """定时偏移的频域因子[K]：正delay使波形延迟，exp(-j2πm*d/N)，m=k-K/2。

        允许分数样点，用于分析理想循环/CP内时移；不是有限波形的分数延迟滤波器。
        """
        delay = real_value("delay_samples", delay_samples)
        bins = np.arange(self.cell.n_subcarriers) - self.cell.n_subcarriers // 2
        return np.exp(-2j * np.pi * bins * delay / self.cell.n_fft)

    def fft_window_phasors(self, advance_samples: int) -> np.ndarray:
        """FFT窗口相对有效起点提前a样点时，恢复网格所乘exp(+j2πm*a/N)。"""
        _integer("advance_samples", advance_samples, 0, self.cell.n_fft - 1)
        return self.timing_phasors(-advance_samples)
