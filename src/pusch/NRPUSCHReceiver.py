"""Known sync, joint time/frequency OCC DMRS LS, per-RB ZF MIMO and UL-SCH decode."""
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
    max_condition_number: float = 1e8

    def __post_init__(self):
        if not isinstance(self.resource,NRPUSCH):
            raise TypeError('resource must be NRPUSCH')
        r=self.resource;NRULSCHCode(self.n_bits,self.target_code_rate,r.coded_length,r.modulation_order,self.redundancy_version,self.max_iterations)
        NROFDM(r.cell,self.carrier_frequency_hz);NRStagePlotter(self.plot_config)
        real_value('detection_threshold',self.detection_threshold,0,1)
        real_value('max_condition_number',self.max_condition_number,1)
        if self.resource.cell.n_rx_antennas<self.resource.n_layers:
            raise ValueError('ZF receiver requires n_rx_antennas >= n_layers')

    def receive(self,waveform,*,known_frequency_offset_hz=0.,known_initial_phase_rad=0.,known_delay_samples=0,cp_fraction=1.,plotter=None):
        r=self.resource;cell=r.cell;y=np.asarray(waveform,dtype=complex)
        if y.shape!=(cell.n_rx_antennas,cell.samples_per_slot) or not np.all(np.isfinite(y)):
            raise ValueError('finite current-slot [Rx,T] waveform required')
        trace=NRStagePlotter(self.plot_config) if plotter is None else plotter;ch=NRChannel(cell)
        corrected=ch.frequency_offset(y,-real_value('CFO',known_frequency_offset_hz),-real_value('phase',known_initial_phase_rad))
        corrected=ch.timing_advance(corrected,known_delay_samples)
        grid=NROFDM(cell,self.carrier_frequency_hz).demodulate(corrected,cp_fraction,plotter=trace)
        # Joint LS over the actual port signatures: frequency/time OCC is retained.
        # Unknown channel [Rx,layer] is assumed constant over each RB and allocation.
        pi=r.indices(True);reference=r.dmrs();pilot_map={}
        for coordinate,value in zip(pi,reference):
            layer,l,k=map(int,coordinate)
            pilot_map.setdefault((l,k),np.zeros(r.n_layers,dtype=complex))[layer]=value
        first=12*(cell.bwp_start-cell.n_start_grid+r.prb)
        di=r.indices();di=di[di[:,0]==0];rb=(di[:,2]-first)//12
        data=grid[:,di[:,1],di[:,2]]
        h=np.zeros((cell.n_rx_antennas,r.n_layers,r.n_prbs),dtype=complex)
        layer_symbols=np.zeros((r.n_layers,len(di)),dtype=complex)
        layer_weights=np.zeros((r.n_layers,len(di)))
        conditions=[];fitted=0.;energy=0.;equalizer_ok=True
        for b in range(r.n_prbs):
            keys=sorted(key for key in pilot_map if (key[1]-first)//12==b)
            design=np.array([pilot_map[key] for key in keys])
            observations=grid[:,[key[0] for key in keys],[key[1] for key in keys]]
            estimate=observations@np.linalg.pinv(design).T
            h[:,:,b]=estimate
            fitted+=float(np.sum(abs(estimate@design.T)**2));energy+=float(np.sum(abs(observations)**2))
            condition=float(np.linalg.cond(estimate));conditions.append(condition)
            if not np.isfinite(condition) or condition>self.max_condition_number or np.linalg.matrix_rank(estimate)<r.n_layers:
                equalizer_ok=False
                continue
            weights=np.linalg.pinv(estimate)
            selected=np.flatnonzero(rb==b)
            layer_symbols[:,selected]=weights@data[:,selected]
            # Relative post-ZF reliability for spatially white equal-variance noise.
            variance=np.sum(abs(weights)**2,axis=1)
            layer_weights[:,selected]=(1/variance)[:,None]
        # Inverse of round-robin layer mapping before codeword descrambling/decoding.
        equalized=layer_symbols.T.ravel();weight=layer_weights.T.ravel()
        constellation,labels=r.constellation();distance=abs(equalized[:,None]-constellation[None,:])**2
        soft=np.array([np.min(distance[:,labels[:,b]==1],axis=1)-np.min(distance[:,labels[:,b]==0],axis=1) for b in range(r.modulation_order)]).T
        soft=(soft*weight[:,None]).ravel()*(1-2*r.scrambling().astype(int))
        codec=NRULSCHCode(self.n_bits,self.target_code_rate,r.coded_length,r.modulation_order,self.redundancy_version,self.max_iterations)
        metric=float(np.clip(fitted/energy,0,1)) if energy else 0.
        detected=metric>self.detection_threshold and fitted>1e-20
        result=codec.decode(soft) if detected and equalizer_ok else dict(bits=None,crc_ok=False,converged=False,iterations=0)
        trace.record('rx.channel',h.reshape(cell.n_rx_antennas*r.n_layers,r.n_prbs),kind='sequence',title='DMRS joint-LS channel estimates per RB')
        trace.record('rx.equalized',layer_symbols,kind='constellation',title='PUSCH ZF QAM, one branch per layer',xlabel='I',ylabel='Q',branch_prefix='Layer')
        trace.record('rx.soft_bits',soft,kind='sequence',title='Descrambled max-log soft scores')
        if plotter is None:trace.show()
        return dict(**result,detected=detected,metric=metric,equalizer_ok=bool(equalizer_ok),
                    condition_numbers=np.array(conditions),equalized_symbols=equalized,layer_symbols=layer_symbols,
                    soft_bits=soft,channel_estimates=h[:,0,:] if r.n_layers==1 else h,channel_matrix=h,rx_grid=grid)
