"""单时隙NR CP-OFDM；TS38.211 V15.2.0 §5.3.1/5.4，单numerology，零加窗。"""

from dataclasses import dataclass

import numpy as np

from cell import NRCell
from common.NRPhaseRotation import NRPhaseRotation
from common._validation import real_value, waveform_array


@dataclass(frozen=True, slots=True)
class NROFDM:
    """IFFT采用1/N、FFT不缩放，对齐MATLAB显式Nfft/Windowing=0，不进行重采样。"""

    cell: NRCell
    carrier_frequency_hz: float = 0.0

    def __post_init__(self):
        """复用NRPhaseRotation对cell/载频的校验。"""
        NRPhaseRotation(self.cell,self.carrier_frequency_hz)

    def modulate(self, grid: np.ndarray) -> np.ndarray:
        """[port,L,K] -> [port,sample]；精确CP、居中载波、逐符号发送相位补偿。"""
        rotated = NRPhaseRotation(self.cell,self.carrier_frequency_hz).apply_grid(grid)
        start = (self.cell.n_fft-self.cell.n_subcarriers)//2
        spectrum = np.zeros((rotated.shape[0],self.cell.symbols_per_slot,self.cell.n_fft),dtype=complex)
        spectrum[:,:,start:start+self.cell.n_subcarriers] = rotated
        useful = np.fft.ifft(np.fft.ifftshift(spectrum,axes=2),axis=2)
        return np.concatenate([np.concatenate((useful[:,l,-cp:],useful[:,l]),axis=1)
                               for l,cp in enumerate(self.cell.slot_cp_lengths_samples)],axis=1)

    def demodulate(self, waveform: np.ndarray, cp_fraction: float = 1.0) -> np.ndarray:
        """[Rx,sample] -> [Rx,L,K]；输入恰好一个当前时隙，已完成粗定时/CFO校正。

        FFT起点CP_start+floor(cp_fraction*CP)，支持[0,1]；自动补偿提前窗口相位。
        不自动估计频偏、TA、用户位置或丢失样点；不裁剪额外波形。
        """
        values = waveform_array(waveform)
        fraction = real_value("cp_fraction",cp_fraction,0,1)
        if values.shape[1] != self.cell.samples_per_slot:
            raise ValueError("waveform must contain exactly the current NRCell slot")
        phase = NRPhaseRotation(self.cell,self.carrier_frequency_hz)
        result = np.empty((values.shape[0],self.cell.symbols_per_slot,self.cell.n_subcarriers),dtype=complex)
        start = (self.cell.n_fft-self.cell.n_subcarriers)//2
        position = 0
        for l,cp in enumerate(self.cell.slot_cp_lengths_samples):
            offset = int(np.floor(fraction*cp))
            window = values[:,position+offset:position+offset+self.cell.n_fft]
            spectrum = np.fft.fftshift(np.fft.fft(window,axis=1),axes=1)
            result[:,l] = spectrum[:,start:start+self.cell.n_subcarriers]*phase.fft_window_phasors(cp-offset)
            position += cp+self.cell.n_fft
        return phase.apply_grid(result,inverse=True)
