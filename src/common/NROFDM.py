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
        NRPhaseRotation(self.cell, self.carrier_frequency_hz)

    def modulate(self, grid: np.ndarray, *, plotter=None) -> np.ndarray:
        """[port,L,K] -> [port,sample]；精确CP、居中载波、逐符号发送相位补偿。"""
        trace = plotter if plotter is not None and plotter.config.enabled else None
        phase = NRPhaseRotation(self.cell, self.carrier_frequency_hz)
        rotated = phase.apply_grid(grid)
        if trace is not None:
            trace.record(
                "tx.symbol_phase",
                phase.symbol_phases(),
                kind="metric",
                title="NR per-symbol phase",
                xlabel="Slot symbol",
                ylabel="Phase (rad)",
            )
            trace.record(
                "tx.phase_compensated_grid",
                rotated,
                kind="grid",
                title="Grid after NR phase rotation",
                xlabel="Slot symbol",
                ylabel="Carrier-local subcarrier",
            )
        start = (self.cell.n_fft - self.cell.n_subcarriers) // 2
        spectrum = np.zeros(
            (rotated.shape[0], self.cell.symbols_per_slot, self.cell.n_fft),
            dtype=complex,
        )
        spectrum[:, :, start : start + self.cell.n_subcarriers] = rotated
        useful = np.fft.ifft(np.fft.ifftshift(spectrum, axes=2), axis=2)
        waveform = np.concatenate(
            [
                np.concatenate((useful[:, l, -cp:], useful[:, l]), axis=1)
                for l, cp in enumerate(self.cell.slot_cp_lengths_samples)
            ],
            axis=1,
        )
        if trace is not None:
            trace.record(
                "tx.fft_spectrum",
                spectrum,
                kind="grid",
                title="Centered FFT spectrum, including zero padding",
                xlabel="Slot symbol",
                ylabel="Centered FFT-array index",
            )
            trace.record(
                "tx.ifft_useful",
                useful.reshape(useful.shape[0], -1),
                title="IFFT output; useful symbols concatenated without CP",
            )
            trace.record(
                "tx.cp_waveform", waveform, title="CP inserted; actual slot waveform"
            )
        return waveform

    def demodulate(
        self, waveform: np.ndarray, cp_fraction: float = 1.0, *, plotter=None
    ) -> np.ndarray:
        """[Rx,sample] -> [Rx,L,K]；输入恰好一个当前时隙，已完成粗定时/CFO校正。

        FFT起点CP_start+floor(cp_fraction*CP)，支持[0,1]；自动补偿提前窗口相位。
        不自动估计频偏、TA、用户位置或丢失样点；不裁剪额外波形。
        """
        values = waveform_array(waveform)
        fraction = real_value("cp_fraction", cp_fraction, 0, 1)
        if values.shape[1] != self.cell.samples_per_slot:
            raise ValueError("waveform must contain exactly the current NRCell slot")
        phase = NRPhaseRotation(self.cell, self.carrier_frequency_hz)
        result = np.empty(
            (values.shape[0], self.cell.symbols_per_slot, self.cell.n_subcarriers),
            dtype=complex,
        )
        start = (self.cell.n_fft - self.cell.n_subcarriers) // 2
        trace = plotter if plotter is not None and plotter.config.enabled else None
        windows = []
        spectra = []
        extracted = []
        position = 0
        for l, cp in enumerate(self.cell.slot_cp_lengths_samples):
            offset = int(np.floor(fraction * cp))
            window = values[:, position + offset : position + offset + self.cell.n_fft]
            spectrum = np.fft.fftshift(np.fft.fft(window, axis=1), axes=1)
            cropped = spectrum[:, start : start + self.cell.n_subcarriers]
            result[:, l] = cropped * phase.fft_window_phasors(cp - offset)
            if trace is not None:
                windows.append(window)
                spectra.append(spectrum)
                extracted.append(cropped)
            position += cp + self.cell.n_fft
        grid = phase.apply_grid(result, inverse=True)
        if trace is not None:
            trace.record(
                "rx.fft_windows",
                np.concatenate(windows, axis=1),
                title="CP-window selection; selected FFT samples concatenated",
            )
            trace.record(
                "rx.fft_spectrum",
                np.stack(spectra, axis=1),
                kind="grid",
                title="FFT + fftshift",
                xlabel="Slot symbol",
                ylabel="Centered FFT-array index",
            )
            trace.record(
                "rx.cropped_grid",
                np.stack(extracted, axis=1),
                kind="grid",
                title="Extracted carrier, before FFT-window phase correction",
                xlabel="Slot symbol",
                ylabel="Carrier-local subcarrier",
            )
            trace.record(
                "rx.window_corrected_grid",
                result,
                kind="grid",
                title="FFT-window phase correction applied",
                xlabel="Slot symbol",
                ylabel="Carrier-local subcarrier",
            )
            trace.record(
                "rx.phase_corrected_grid",
                grid,
                kind="grid",
                title="NR symbol phase removed",
                xlabel="Slot symbol",
                ylabel="Carrier-local subcarrier",
            )
        return grid
