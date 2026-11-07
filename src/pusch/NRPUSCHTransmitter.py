"""One-codeword multilayer UL-SCH transport block -> coded PUSCH/DMRS -> OFDM waveform."""
from dataclasses import dataclass
from common import NROFDM
from common.NRULSCHCode import NRULSCHCode
from diagnostics import NRPlotConfig,NRStagePlotter
from grid import NRGrid
from pusch.NRPUSCH import NRPUSCH


@dataclass(frozen=True,slots=True)
class NRPUSCHTransmitter:
    resource: NRPUSCH
    target_code_rate: float = .5
    redundancy_version: int = 0
    carrier_frequency_hz: float = 0.
    plot_config: NRPlotConfig | None = None

    def __post_init__(self):
        if not isinstance(self.resource,NRPUSCH):
            raise TypeError('resource must be NRPUSCH')
        NRULSCHCode(16,self.target_code_rate,self.resource.coded_length,self.resource.modulation_order,self.redundancy_version)
        NROFDM(self.resource.cell,self.carrier_frequency_hz);NRStagePlotter(self.plot_config)

    def transmit(self,bits,beta=1.,*,plotter=None):
        bits=tuple(bits);r=self.resource
        codec=NRULSCHCode(len(bits),self.target_code_rate,r.coded_length,r.modulation_order,self.redundancy_version)
        if len(bits)+codec.crc_length>r.coded_length*.95:
            raise ValueError('insufficient resources for transport block')
        coded=codec.encode(bits);grid=NRGrid(r.cell,r.n_layers);r.map_to_grid(grid,coded,beta)
        trace=NRStagePlotter(self.plot_config) if plotter is None else plotter
        trace.record('tx.coded_bits',coded,kind='metric',title='UL-SCH rate-matched bits')
        trace.record('tx.modulation',r.generate(coded).reshape(r.n_layers,-1),kind='constellation',title='PUSCH scrambled QAM by layer',xlabel='I',ylabel='Q',branch_prefix='Layer')
        trace.record('tx.grid',grid.data,kind='grid',title=f'PUSCH data / type{r.dmrs_configuration_type} DMRS')
        wave=NROFDM(r.cell,self.carrier_frequency_hz).modulate(grid.data,plotter=trace)
        if plotter is None:trace.show()
        return dict(waveform=wave,grid=grid,coded_bits=coded,base_graph=codec.base_graph,lifting_size=codec.lifting_size)
