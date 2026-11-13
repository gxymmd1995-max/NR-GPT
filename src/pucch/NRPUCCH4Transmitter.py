"""F4 UCI common coding -> DFT precoding/DMRS -> OFDM waveform."""

from dataclasses import dataclass
from common import NROFDM
from common.NRUCICode import NRUCICode
from diagnostics import NRPlotConfig, NRStagePlotter
from grid import NRGrid
from pucch.NRPUCCH4 import NRPUCCH4


@dataclass(frozen=True, slots=True)
class NRPUCCH4Transmitter:
    resource: NRPUCCH4
    carrier_frequency_hz: float = 0.0
    plot_config: NRPlotConfig | None = None

    def __post_init__(self):
        if not isinstance(self.resource, NRPUCCH4):
            raise TypeError("resource must be NRPUCCH4")
        NROFDM(self.resource.cell, self.carrier_frequency_hz)
        NRStagePlotter(self.plot_config)

    def transmit(self, bits, beta=1.0, *, plotter=None):
        bits = tuple(bits)
        code = NRUCICode(len(bits), self.resource.coded_length)
        if (
            len(bits) + code.crc_length * code.n_blocks
        ) > 0.6 * self.resource.coded_length:
            raise ValueError("code rate exceeds 0.6")
        trace = NRStagePlotter(self.plot_config) if plotter is None else plotter
        coded = code.encode(bits)
        grid = NRGrid(self.resource.cell, 1)
        self.resource.map_to_grid(grid, coded, beta)
        trace.record("tx.coded_bits", coded, kind="metric", title="F4 UCI encoded bits")
        trace.record(
            "tx.occ",
            self.resource.occ(),
            kind="sequence",
            title="F4 frequency-domain OCC",
        )
        trace.record(
            "tx.transform_precoded",
            self.resource.generate(coded),
            kind="sequence",
            title="Unitary DFT precoded data",
        )
        trace.record("tx.mapped_grid", grid.data, kind="grid", title="F4 data and DMRS")
        wave = NROFDM(self.resource.cell, self.carrier_frequency_hz).modulate(
            grid.data, plotter=trace
        )
        if plotter is None:
            trace.show()
        return dict(
            waveform=wave,
            grid=grid,
            coded_bits=coded,
            symbols=self.resource.generate(coded),
        )
