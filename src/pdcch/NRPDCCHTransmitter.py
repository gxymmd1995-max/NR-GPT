"""PDCCH DCI Polar编码→加扰QPSK/DMRS→OFDM完整slot。"""
from dataclasses import dataclass
from common.NRCommon import _integer
from common import NROFDM
from common.NRDCICode import NRDCICode
from diagnostics import NRPlotConfig,NRStagePlotter
from grid import NRGrid
from pdcch.NRPDCCH import NRPDCCH


@dataclass(frozen=True,slots=True)
class NRPDCCHTransmitter:
    resource: NRPDCCH
    rnti: int = 1
    carrier_frequency_hz: float = 0.
    plot_config: NRPlotConfig | None = None

    def __post_init__(self):
        if not isinstance(self.resource,NRPDCCH):
            raise TypeError('resource must be NRPDCCH')
        _integer('rnti',self.rnti,0,65535)
        NROFDM(self.resource.cell,self.carrier_frequency_hz)
        NRStagePlotter(self.plot_config)

    def transmit(self,bits,beta=1.,*,plotter=None):
        bits=tuple(bits)
        codec=NRDCICode(len(bits),self.resource.coded_length,self.rnti)
        trace=NRStagePlotter(self.plot_config) if plotter is None else plotter
        coded=codec.encode(bits)
        grid=NRGrid(self.resource.cell,1)
        self.resource.map_to_grid(grid,coded,beta)
        trace.record('tx.coded_bits',coded,kind='metric',title='Rate-matched DCI bits')
        trace.record('tx.qpsk',self.resource.generate(coded),kind='constellation',title='Scrambled QPSK',xlabel='I (normalized amplitude)',ylabel='Q (normalized amplitude)')
        trace.record('tx.mapped_grid',grid.data,kind='grid',title='PDCCH data and DMRS')
        wave=NROFDM(self.resource.cell,self.carrier_frequency_hz).modulate(grid.data,plotter=trace)
        if plotter is None:
            trace.show()
        return dict(waveform=wave,grid=grid,coded_bits=coded,symbols=self.resource.generate(coded))
