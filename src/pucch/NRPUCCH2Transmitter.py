"""F2 UCI小块编码→加扰QPSK/DMRS→OFDM完整slot。"""
from dataclasses import dataclass
from common import NROFDM
from common.NRUCICode import NRUCICode
from diagnostics import NRPlotConfig,NRStagePlotter
from grid import NRGrid
from pucch.NRPUCCH2 import NRPUCCH2


@dataclass(frozen=True,slots=True)
class NRPUCCH2Transmitter:
    resource: NRPUCCH2
    carrier_frequency_hz: float = 0.
    plot_config: NRPlotConfig | None = None

    def __post_init__(self):
        if not isinstance(self.resource,NRPUCCH2):
            raise TypeError('resource must be NRPUCCH2')
        NROFDM(self.resource.cell,self.carrier_frequency_hz)
        NRStagePlotter(self.plot_config)

    def transmit(self,bits,beta=1.,*,plotter=None):
        bits=tuple(bits)
        codec=NRUCICode(len(bits),self.resource.coded_length)
        if len(bits)+codec.crc_length*codec.n_blocks > .6*self.resource.coded_length:
            raise ValueError('UCI exceeds maximum supported code rate 0.6; allocate more PRBs')
        trace=NRStagePlotter(self.plot_config) if plotter is None else plotter
        coded=codec.encode(bits)
        grid=NRGrid(self.resource.cell,1)
        self.resource.map_to_grid(grid,coded,beta)
        trace.record('tx.coded_bits',coded,kind='metric',title='Rate-matched UCI bits')
        trace.record('tx.qpsk',self.resource.generate(coded),kind='constellation',title='Scrambled QPSK',xlabel='I (normalized amplitude)',ylabel='Q (normalized amplitude)')
        trace.record('tx.mapped_grid',grid.data,kind='grid',title='F2 data and DMRS')
        wave=NROFDM(self.resource.cell,self.carrier_frequency_hz).modulate(grid.data,plotter=trace)
        if plotter is None:
            trace.show()
        return dict(waveform=wave,grid=grid,coded_bits=coded,symbols=self.resource.generate(coded))
