"""One-codeword multilayer DL-SCH transport block -> coded PDSCH/DMRS -> OFDM waveform."""

from dataclasses import dataclass
from common import NROFDM
from common.NRDLSCHCode import NRDLSCHCode
from diagnostics import NRPlotConfig, NRStagePlotter
from grid import NRGrid
from pdsch.NRPDSCH import NRPDSCH


@dataclass(frozen=True, slots=True)
class NRPDSCHTransmitter:
    resource: NRPDSCH
    target_code_rate: float = 0.5
    redundancy_version: int = 0
    carrier_frequency_hz: float = 0.0
    plot_config: NRPlotConfig | None = None
    n_ref: int | None = None

    def __post_init__(self):
        if not isinstance(self.resource, NRPDSCH):
            raise TypeError("resource must be NRPDSCH")
        NRDLSCHCode(
            16,
            self.target_code_rate,
            self.resource.coded_length,
            self.resource.modulation_order,
            self.redundancy_version,
            n_ref=self.n_ref,
        )
        NROFDM(self.resource.cell, self.carrier_frequency_hz)
        NRStagePlotter(self.plot_config)

    def transmit(self, bits, beta=1.0, *, plotter=None):
        bits = tuple(bits)
        r = self.resource
        codec = NRDLSCHCode(
            len(bits),
            self.target_code_rate,
            r.coded_length,
            r.modulation_order,
            self.redundancy_version,
            n_ref=self.n_ref,
        )
        if len(bits) + codec.crc_length > r.coded_length * 0.95:
            raise ValueError("insufficient resources for transport block")
        coded = codec.encode(bits)
        grid = NRGrid(r.cell, r.n_layers)
        r.map_to_grid(grid, coded, beta)
        trace = NRStagePlotter(self.plot_config) if plotter is None else plotter
        trace.record(
            "tx.coded_bits", coded, kind="metric", title="DL-SCH rate-matched bits"
        )
        trace.record(
            "tx.modulation",
            r.generate(coded).reshape(r.n_layers, -1),
            kind="constellation",
            title="PDSCH scrambled QAM by layer",
            xlabel="I",
            ylabel="Q",
            branch_prefix="Layer",
        )
        trace.record("tx.grid", grid.data, kind="grid", title="PDSCH data / type1 DMRS")
        wave = NROFDM(r.cell, self.carrier_frequency_hz).modulate(
            grid.data, plotter=trace
        )
        if plotter is None:
            trace.show()
        return dict(
            waveform=wave,
            grid=grid,
            coded_bits=coded,
            base_graph=codec.base_graph,
            lifting_size=codec.lifting_size,
        )
