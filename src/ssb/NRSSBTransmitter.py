"""BCH transport block -> payload/timing/CRC/Polar -> SS/PBCH grid -> slot OFDM."""

from dataclasses import dataclass
from common.NRBCHCode import NRBCHCode
from common import NROFDM
from grid import NRGrid
from diagnostics import NRPlotConfig, NRStagePlotter
from .NRSSB import NRSSB


@dataclass(frozen=True, slots=True)
class NRSSBTransmitter:
    resource: NRSSB
    carrier_frequency_hz: float = 0.0
    plot_config: NRPlotConfig | None = None

    def __post_init__(self):
        if not isinstance(self.resource, NRSSB):
            raise TypeError("resource must be NRSSB")
        NROFDM(self.resource.cell, self.carrier_frequency_hz)
        NRStagePlotter(self.plot_config)

    def transmit(self, mib, sfn_lsb=0, beta=1.0, *, plotter=None):
        r = self.resource
        coded = NRBCHCode(
            r.cell.n_cell_id, r.l_max, r.ssb_index, r.half_frame, r.k_ssb
        ).encode(mib, sfn_lsb)
        grid = NRGrid(r.cell, 1)
        r.map_to_grid(grid, coded, beta)
        trace = NRStagePlotter(self.plot_config) if plotter is None else plotter
        trace.record(
            "tx.pss", r.pss(r.cell.n_id_2), kind="sequence", title="127-point PSS"
        )
        trace.record(
            "tx.sss", r.sss(r.cell.n_cell_id), kind="sequence", title="127-point SSS"
        )
        trace.record(
            "tx.bch_bits", coded, kind="metric", title="BCH rate-matched Polar bits"
        )
        trace.record(
            "tx.pbch",
            r.generate(coded),
            kind="constellation",
            title="Scrambled PBCH QPSK",
            xlabel="I",
            ylabel="Q",
        )
        trace.record(
            "tx.grid", grid.data, kind="grid", title="PSS / SSS / PBCH / PBCH DMRS"
        )
        wave = NROFDM(r.cell, self.carrier_frequency_hz).modulate(
            grid.data, plotter=trace
        )
        if plotter is None:
            trace.show()
        return dict(waveform=wave, grid=grid, coded_bits=coded)
