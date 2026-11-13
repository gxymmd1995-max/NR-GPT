"""Known SS/PBCH time-frequency occasion; blind PCI/PBCH-DMRS index, LS/MRC and BCH SC/CRC."""

from dataclasses import dataclass, replace
import numpy as np
from common import NROFDM
from common.NRBCHCode import NRBCHCode
from common._validation import real_value, waveform_array
from channel import NRChannel
from diagnostics import NRPlotConfig, NRStagePlotter
from .NRSSB import NRSSB


@dataclass(frozen=True, slots=True)
class NRSSBReceiver:
    resource: NRSSB
    carrier_frequency_hz: float = 0.0
    detection_threshold: float = 0.1
    plot_config: NRPlotConfig | None = None

    def __post_init__(self):
        if not isinstance(self.resource, NRSSB):
            raise TypeError("resource must be NRSSB")
        real_value("detection_threshold", self.detection_threshold, 0, 1)
        NROFDM(self.resource.cell, self.carrier_frequency_hz)
        NRStagePlotter(self.plot_config)

    def receive(
        self,
        waveform,
        *,
        known_delay_samples=0,
        known_frequency_offset_hz=0.0,
        known_initial_phase_rad=0.0,
        plotter=None,
    ):
        r = self.resource
        cell = r.cell
        y = waveform_array(waveform)
        if y.shape != (cell.n_rx_antennas, cell.samples_per_slot):
            raise ValueError("current slot [Rx,T] waveform required")
        trace = NRStagePlotter(self.plot_config) if plotter is None else plotter
        channel = NRChannel(cell)
        y = channel.frequency_offset(
            y,
            -real_value("CFO", known_frequency_offset_hz),
            -real_value("phase", known_initial_phase_rad),
        )
        y = channel.timing_advance(y, known_delay_samples)
        grid = NROFDM(cell, self.carrier_frequency_hz).demodulate(y, plotter=trace)
        p = r.indices("pss")
        s = r.indices("sss")
        yp = grid[:, p[:, 1], p[:, 2]]
        ys = grid[:, s[:, 1], s[:, 2]]

        def metrics(observed, refs):
            energy = float(np.sum(abs(observed) ** 2))
            power = np.sum(abs(observed @ np.asarray(refs).conj().T) ** 2, axis=0)
            return (
                np.clip(power / (127 * energy), 0, 1)
                if energy > 0
                else np.zeros(len(refs))
            )

        pmetrics = metrics(yp, [NRSSB.pss(i) for i in range(3)])
        nid2 = int(np.argmax(pmetrics))
        smetrics = metrics(ys, [NRSSB.sss(3 * i + nid2) for i in range(336)])
        pci = 3 * int(np.argmax(smetrics)) + nid2
        detected = bool(
            pmetrics[nid2] > self.detection_threshold
            and np.max(smetrics) > self.detection_threshold
        )
        found = replace(r, cell=replace(cell, n_cell_id=pci))
        scores = []
        refs = []
        for index in range(8):
            candidate = replace(
                found,
                ssb_index=index % r.l_max,
                half_frame=index // 4 if r.l_max == 4 else found.half_frame,
            )
            ref = candidate.dmrs()
            refs.append(ref)
            pi = candidate.indices("dmrs")
            pilots = grid[:, pi[:, 1], pi[:, 2]]
            scores.append(float(np.sum(abs(pilots @ ref.conj()) ** 2)))
        index = int(np.argmax(scores))
        found = replace(
            found,
            ssb_index=index % r.l_max,
            half_frame=index // 4 if r.l_max == 4 else found.half_frame,
        )
        pi = found.indices("dmrs")
        di = found.indices("pbch")
        ref = refs[index]
        h = np.zeros((cell.n_rx_antennas, 3), complex)
        numerator = []
        weights = []
        for j, symbol in enumerate(range(r.start_symbol + 1, r.start_symbol + 4)):
            mask = pi[:, 1] == symbol
            pilot = grid[:, pi[mask, 1], pi[mask, 2]]
            h[:, j] = np.mean(pilot * ref[mask].conj(), axis=1)
            data = di[di[:, 1] == symbol]
            numerator.extend(
                np.sum(
                    h[:, j].conj()[:, None] * grid[:, data[:, 1], data[:, 2]], axis=0
                )
            )
            weights.extend([np.sum(abs(h[:, j]) ** 2)] * len(data))
        numerator = np.asarray(numerator)
        weights = np.asarray(weights)
        equalized = np.divide(
            numerator, weights, out=np.zeros_like(numerator), where=weights > 1e-20
        )
        llr = np.stack([numerator.real, numerator.imag], axis=1).ravel() * (
            1 - 2 * found.scrambling().astype(int)
        )
        decoded = (
            NRBCHCode(pci, r.l_max, found.ssb_index, found.half_frame, r.k_ssb).decode(
                llr
            )
            if detected
            else dict(
                mib=None,
                sfn_lsb=None,
                system_frame_number=None,
                half_frame=None,
                extra_bits=None,
                crc_ok=False,
            )
        )
        full_index = found.ssb_index
        if r.l_max == 64 and decoded["crc_ok"]:
            full_index = index + 8 * int(
                np.array(decoded["extra_bits"]) @ np.array([4, 2, 1])
            )
        trace.record("rx.pss_metrics", pmetrics, kind="metric", title="PSS NID2 search")
        trace.record("rx.sss_metrics", smetrics, kind="metric", title="SSS NID1 search")
        trace.record(
            "rx.dmrs_metrics", scores, kind="metric", title="PBCH DMRS index search"
        )
        trace.record(
            "rx.pbch",
            equalized,
            kind="constellation",
            title="PBCH LS/MRC QPSK",
            xlabel="I",
            ylabel="Q",
        )
        if plotter is None:
            trace.show()
        return dict(
            **decoded,
            detected=detected,
            cell_id=pci if detected else None,
            ssb_index=full_index if detected else None,
            pss_metrics=pmetrics,
            sss_metrics=smetrics,
            channel_estimates=h,
            equalized_symbols=equalized,
            rx_grid=grid,
        )
