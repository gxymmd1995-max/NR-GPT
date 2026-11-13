"""F1数据/DMRS→资源网格→带CP及NR相位补偿的时域波形。"""

from dataclasses import dataclass
from common import NROFDM
from diagnostics import NRStagePlotter, NRPlotConfig
from grid import NRGrid
from pucch.NRPUCCH1 import NRPUCCH1


@dataclass(frozen=True, slots=True)
class NRPUCCH1Transmitter:
    resource: NRPUCCH1
    carrier_frequency_hz: float = 0.0
    plot_config: NRPlotConfig | None = None

    def __post_init__(self):
        if not isinstance(self.resource, NRPUCCH1):
            raise TypeError("resource must be NRPUCCH1")
        NROFDM(self.resource.cell, self.carrier_frequency_hz)
        NRStagePlotter(self.plot_config)

    def transmit(self, bits, beta=1.0, *, plotter=None):
        trace = NRStagePlotter(self.plot_config) if plotter is None else plotter
        grid = NRGrid(self.resource.cell, 1)
        self.resource.map_to_grid(grid, bits, beta)
        trace.record(
            "tx.reference",
            self.resource.reference(),
            kind="sequence",
            title="F1 reference with OCC",
        )
        trace.record("tx.mapped_grid", grid.data, kind="grid", title="F1 data and DMRS")
        waveform = NROFDM(self.resource.cell, self.carrier_frequency_hz).modulate(
            grid.data, plotter=trace
        )
        if plotter is None:
            trace.show()
        return dict(
            waveform=waveform,
            grid=grid,
            symbols=self.resource.generate(bits),
            indices=self.resource.indices(),
        )
