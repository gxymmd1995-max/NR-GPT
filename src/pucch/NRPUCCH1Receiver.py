"""F1工程接收机：已知同步、逐跳DMRS平坦信道估计、MRC及BPSK/QPSK判决。"""

from dataclasses import dataclass
import numpy as np
from common import NROFDM
from common.NRCommon import _integer
from common._validation import real_value
from channel import NRChannel
from diagnostics import NRStagePlotter, NRPlotConfig
from pucch.NRPUCCH1 import NRPUCCH1


@dataclass(frozen=True, slots=True)
class NRPUCCH1Receiver:
    resource: NRPUCCH1
    n_bits: int = 1
    carrier_frequency_hz: float = 0.0
    detection_threshold: float = 0.1
    plot_config: NRPlotConfig | None = None

    def __post_init__(self):
        if not isinstance(self.resource, NRPUCCH1):
            raise TypeError("resource must be NRPUCCH1")
        _integer("n_bits", self.n_bits, 1, 2)
        real_value("detection_threshold", self.detection_threshold, 0, 1)
        NROFDM(self.resource.cell, self.carrier_frequency_hz)
        NRStagePlotter(self.plot_config)

    def receive(
        self,
        waveform,
        *,
        known_frequency_offset_hz=0.0,
        known_initial_phase_rad=0.0,
        known_delay_samples=0,
        cp_fraction=1.0,
        plotter=None,
    ):
        cell = self.resource.cell
        values = np.asarray(waveform, dtype=complex)
        if values.shape != (cell.n_rx_antennas, cell.samples_per_slot) or not np.all(
            np.isfinite(values)
        ):
            raise ValueError("waveform must be finite [Rx,T] for the current slot")
        trace = NRStagePlotter(self.plot_config) if plotter is None else plotter
        channel = NRChannel(cell)
        corrected = channel.frequency_offset(
            values,
            -real_value("CFO", known_frequency_offset_hz),
            -real_value("phase", known_initial_phase_rad),
        )
        corrected = channel.timing_advance(corrected, known_delay_samples)
        grid = NROFDM(cell, self.carrier_frequency_hz).demodulate(
            corrected, cp_fraction, plotter=trace
        )
        idx = self.resource.indices()
        y = grid[:, idx[:, 1], idx[:, 2]].reshape(
            cell.n_rx_antennas, self.resource.n_symbols, 12
        )
        projection = np.mean(y * self.resource.reference().conj()[None, :, :], axis=-1)
        estimates = []
        numerator = 0j
        denominator = 0.0
        fitted_energy = 0.0
        parity = np.arange(self.resource.n_symbols) % 2
        for hop in np.unique(self.resource.hops):
            dmrs = (self.resource.hops == hop) & (parity == 0)
            data = (self.resource.hops == hop) & (parity == 1)
            h = np.mean(projection[:, dmrs], axis=1)
            estimates.append(h)
            numerator += np.sum(h.conj()[:, None] * projection[:, data])
            denominator += np.sum(abs(h) ** 2) * np.count_nonzero(data)
            fitted_energy += 12 * np.count_nonzero(dmrs) * np.sum(abs(h) ** 2)
        equalized = numerator / denominator if denominator > 1e-20 else 0j
        dmrs_energy = float(np.sum(abs(y[:, ::2]) ** 2))
        metric = (
            float(np.clip(fitted_energy / dmrs_energy, 0, 1)) if dmrs_energy else 0.0
        )
        detected = metric > self.detection_threshold and denominator > 1e-20
        bits = [int(equalized.real < 0)]
        if self.n_bits == 2:
            bits.append(int(equalized.imag < 0))
        trace.record(
            "rx.despread",
            projection,
            kind="sequence",
            title="Per-symbol despread output",
        )
        trace.record(
            "rx.equalized_constellation",
            [equalized],
            kind="constellation",
            title="DMRS equalized UCI",
        )
        if plotter is None:
            trace.show()
        return dict(
            detected=detected,
            bits=bits if detected else None,
            metric=metric,
            equalized_symbol=equalized,
            channel_estimates=np.array(estimates),
            rx_symbols=y,
            rx_grid=grid,
        )
