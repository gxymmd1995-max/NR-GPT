"""PDCCH工程接收：每符号每RB平坦DMRS估计、MRC、软解扰和小块ML。"""

from dataclasses import dataclass
import numpy as np
from channel import NRChannel
from common import NROFDM
from common.NRCommon import _integer
from common.NRDCICode import NRDCICode
from common._validation import real_value
from diagnostics import NRPlotConfig, NRStagePlotter
from pdcch.NRPDCCH import NRPDCCH


@dataclass(frozen=True, slots=True)
class NRPDCCHReceiver:
    resource: NRPDCCH
    n_bits: int = 3
    rnti: int = 1
    carrier_frequency_hz: float = 0.0
    detection_threshold: float = 0.1
    plot_config: NRPlotConfig | None = None

    def __post_init__(self):
        if not isinstance(self.resource, NRPDCCH):
            raise TypeError("resource must be NRPDCCH")
        _integer("n_bits", self.n_bits, 12, 140)
        codec = NRDCICode(self.n_bits, self.resource.coded_length, self.rnti)
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
        r = self.resource
        y = np.asarray(waveform, dtype=complex)
        if y.shape != (cell.n_rx_antennas, cell.samples_per_slot) or not np.all(
            np.isfinite(y)
        ):
            raise ValueError("finite current-slot [Rx,T] waveform required")
        trace = NRStagePlotter(self.plot_config) if plotter is None else plotter
        channel = NRChannel(cell)
        corrected = channel.frequency_offset(
            y,
            -real_value("CFO", known_frequency_offset_hz),
            -real_value("phase", known_initial_phase_rad),
        )
        corrected = channel.timing_advance(corrected, known_delay_samples)
        grid = NROFDM(cell, self.carrier_frequency_hz).demodulate(
            corrected, cp_fraction, plotter=trace
        )
        di = r.indices()
        pi = r.indices(True)
        data = grid[:, di[:, 1], di[:, 2]].reshape(
            cell.n_rx_antennas, 6 * r.aggregation_level, 9
        )
        pilots = grid[:, pi[:, 1], pi[:, 2]].reshape(
            cell.n_rx_antennas, 6 * r.aggregation_level, 3
        )
        reference = r.dmrs().reshape(6 * r.aggregation_level, 3)
        h = np.mean(pilots * reference.conj()[None, :, :], axis=-1)
        numerator = np.sum(h.conj()[..., None] * data, axis=0)
        weight = np.sum(abs(h) ** 2, axis=0)
        equalized = np.divide(
            numerator,
            weight[..., None],
            out=np.zeros_like(numerator),
            where=weight[..., None] > 1e-20,
        )
        # Soft scores proportional to LLR under common white noise; no calibrated noise variance claimed.
        llr = np.stack([numerator.real, numerator.imag], axis=-1).ravel() * (
            1 - 2 * r.scrambling().astype(int)
        )
        energy = float(np.sum(abs(pilots) ** 2))
        metric = (
            float(np.clip(3 * np.sum(abs(h) ** 2) / energy, 0, 1)) if energy else 0.0
        )
        detected = metric > self.detection_threshold and np.any(weight > 1e-20)
        decoded = (
            NRDCICode(self.n_bits, r.coded_length, self.rnti).decode(llr)
            if detected
            else dict(bits=None, crc_ok=None)
        )
        bits = decoded["bits"]
        trace.record(
            "rx.channel_estimates",
            h.reshape(cell.n_rx_antennas, -1),
            kind="sequence",
            title="Per-symbol per-RB channel estimates",
        )
        trace.record(
            "rx.equalized_constellation",
            equalized.ravel(),
            kind="constellation",
            title="PDCCH equalized QPSK",
            xlabel="I (normalized amplitude)",
            ylabel="Q (normalized amplitude)",
        )
        trace.record(
            "rx.soft_bits", llr, kind="sequence", title="Descrambled soft scores"
        )
        if plotter is None:
            trace.show()
        return dict(
            detected=bool(detected),
            bits=bits,
            crc_ok=decoded["crc_ok"],
            metric=metric,
            soft_bits=llr,
            equalized_symbols=equalized,
            channel_estimates=h,
            rx_grid=grid,
        )
