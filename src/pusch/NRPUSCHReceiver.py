"""Known synchronization, flat-per-RB DMRS estimates/MRC, max-log QAM, UL-SCH decode."""
from dataclasses import dataclass
import numpy as np
from common import NROFDM
from common.NRULSCHCode import NRULSCHCode
from common._validation import real_value
from channel import NRChannel
from diagnostics import NRPlotConfig,NRStagePlotter
from pusch.NRPUSCH import NRPUSCH


@dataclass(frozen=True,slots=True)
class NRPUSCHReceiver:
    resource: NRPUSCH
    n_bits: int
    target_code_rate: float = .5
    redundancy_version: int = 0
    carrier_frequency_hz: float = 0.
    max_iterations: int = 30
    plot_config: NRPlotConfig | None = None
    detection_threshold: float = .1

    def __post_init__(self):
        if not isinstance(self.resource,NRPUSCH):raise TypeError('resource must be NRPUSCH')
        r=self.resource;NRULSCHCode(self.n_bits,self.target_code_rate,r.coded_length,r.modulation_order,self.redundancy_version,self.max_iterations)
        NROFDM(r.cell,self.carrier_frequency_hz);NRStagePlotter(self.plot_config)
        real_value('detection_threshold',self.detection_threshold,0,1)

    def receive(self,waveform,*,known_frequency_offset_hz=0.,known_initial_phase_rad=0.,known_delay_samples=0,cp_fraction=1.,plotter=None):
        r=self.resource;cell=r.cell;y=np.asarray(waveform,dtype=complex)
        if y.shape!=(cell.n_rx_antennas,cell.samples_per_slot) or not np.all(np.isfinite(y)):raise ValueError('finite current-slot [Rx,T] waveform required')
        trace=NRStagePlotter(self.plot_config) if plotter is None else plotter;ch=NRChannel(cell)
        corrected=ch.frequency_offset(y,-real_value('CFO',known_frequency_offset_hz),-real_value('phase',known_initial_phase_rad))
        corrected=ch.timing_advance(corrected,known_delay_samples)
        grid=NROFDM(cell,self.carrier_frequency_hz).demodulate(corrected,cp_fraction,plotter=trace)
        pi=r.indices(True);di=r.indices()
        pilots=grid[:,pi[:,1],pi[:,2]].reshape(cell.n_rx_antennas,r.n_prbs,6)
        reference=r.dmrs().reshape(r.n_prbs,6)
        h=np.mean(pilots*reference.conj()[None,:,:],axis=-1)
        first=12*(cell.bwp_start-cell.n_start_grid+r.prb);rb=(di[:,2]-first)//12
        data=grid[:,di[:,1],di[:,2]];channel=h[:,rb]
        numerator=np.sum(channel.conj()*data,axis=0);weight=np.sum(abs(channel)**2,axis=0)
        equalized=np.divide(numerator,weight,out=np.zeros_like(numerator),where=weight>1e-20)
        constellation,labels=r.constellation();distance=abs(equalized[:,None]-constellation[None,:])**2
        soft=np.array([np.min(distance[:,labels[:,b]==1],axis=1)-np.min(distance[:,labels[:,b]==0],axis=1) for b in range(r.modulation_order)]).T
        soft=(soft*weight[:,None]).ravel()*(1-2*r.scrambling().astype(int))
        codec=NRULSCHCode(self.n_bits,self.target_code_rate,r.coded_length,r.modulation_order,self.redundancy_version,self.max_iterations)
        energy=float(np.sum(abs(pilots)**2))
        metric=float(np.clip(6*np.sum(abs(h)**2)/energy,0,1)) if energy else 0.
        detected=metric>self.detection_threshold and bool(np.any(weight>1e-20))
        result=codec.decode(soft) if detected else dict(bits=None,crc_ok=False,converged=False,iterations=0)
        trace.record('rx.channel',h,kind='sequence',title='DMRS channel estimates per RB')
        trace.record('rx.equalized',equalized,kind='constellation',title='PUSCH MRC QAM',xlabel='I',ylabel='Q')
        trace.record('rx.soft_bits',soft,kind='sequence',title='Descrambled max-log soft scores')
        if plotter is None:trace.show()
        return dict(**result,detected=detected,metric=metric,equalized_symbols=equalized,soft_bits=soft,channel_estimates=h,rx_grid=grid)
