"""F3 known-sync DMRS-assisted flat-per-hop MRC, IDFT despreading, common UCI decode."""
from dataclasses import dataclass
import numpy as np
from common import NROFDM
from common.NRUCICode import NRUCICode
from common._validation import real_value
from channel import NRChannel
from diagnostics import NRPlotConfig,NRStagePlotter
from pucch.NRPUCCH3 import NRPUCCH3


@dataclass(frozen=True,slots=True)
class NRPUCCH3Receiver:
    resource: NRPUCCH3
    n_bits: int = 3
    carrier_frequency_hz: float = 0.
    detection_threshold: float = .1
    plot_config: NRPlotConfig | None = None

    def __post_init__(self):
        if not isinstance(self.resource,NRPUCCH3):raise TypeError('resource must be NRPUCCH3')
        code=NRUCICode(self.n_bits,self.resource.coded_length)
        if (self.n_bits+code.crc_length*code.n_blocks)>.6*self.resource.coded_length:raise ValueError('code rate exceeds 0.6')
        real_value('threshold',self.detection_threshold,0,1)
        NROFDM(self.resource.cell,self.carrier_frequency_hz);NRStagePlotter(self.plot_config)

    def receive(self,waveform,*,known_frequency_offset_hz=0.,known_initial_phase_rad=0.,known_delay_samples=0,cp_fraction=1.,plotter=None):
        r=self.resource;cell=r.cell;y=np.asarray(waveform,dtype=complex)
        if y.shape!=(cell.n_rx_antennas,cell.samples_per_slot) or not np.all(np.isfinite(y)):raise ValueError('finite current-slot [Rx,T] required')
        trace=NRStagePlotter(self.plot_config) if plotter is None else plotter;ch=NRChannel(cell)
        y=ch.frequency_offset(y,-real_value('CFO',known_frequency_offset_hz),-real_value('phase',known_initial_phase_rad));y=ch.timing_advance(y,known_delay_samples)
        grid=NROFDM(cell,self.carrier_frequency_hz).demodulate(y,cp_fraction,plotter=trace)
        di=r.indices();pi=r.indices(True);M=12*r.n_prbs
        data=grid[:,di[:,1],di[:,2]].reshape(cell.n_rx_antennas,-1,M)
        pilots=grid[:,pi[:,1],pi[:,2]].reshape(cell.n_rx_antennas,-1,M)
        reference=r.dmrs().reshape(-1,M);projection=pilots*reference.conj()[None,:,:]
        estimates=[];soft=[];equalized=[];fitted=0.
        for s,symbol in enumerate(r.data_symbols):
            hop=int(r.second_hop_prb is not None and symbol>=r.n_symbols//2)
            mask=np.array([int(r.second_hop_prb is not None and p>=r.n_symbols//2)==hop for p in r.dmrs_symbols])
            h=np.mean(projection[:,mask,:],axis=(1,2));estimates.append(h)
            numerator=np.sum(h.conj()[:,None]*data[:,s,:],axis=0);weight=np.sum(abs(h)**2)
            despread=np.fft.ifft(numerator,norm='ortho');equalized.extend(despread/weight if weight>1e-20 else np.zeros(M))
            soft.extend(despread)
        for hop in range(2 if r.second_hop_prb is not None else 1):
            mask=np.array([int(r.second_hop_prb is not None and p>=r.n_symbols//2)==hop for p in r.dmrs_symbols])
            h=np.mean(projection[:,mask,:],axis=(1,2));fitted+=M*np.count_nonzero(mask)*np.sum(abs(h)**2)
        soft=np.array(soft)
        if r.modulation=='QPSK':llr=np.stack([soft.real,soft.imag],axis=-1).ravel()
        else:llr=(soft*np.exp(-1j*np.pi/2*(np.arange(len(soft))%2))*(1-1j)/np.sqrt(2)).real
        llr*=1-2*r.scrambling().astype(int)
        energy=np.sum(abs(pilots)**2);metric=float(np.clip(fitted/energy,0,1)) if energy else 0.
        detected=metric>self.detection_threshold and fitted>1e-20
        result=NRUCICode(self.n_bits,r.coded_length).decode(llr) if detected else dict(bits=None,crc_ok=None)
        trace.record('rx.idft_constellation',equalized,kind='constellation',title='F3 IDFT equalized modulation',xlabel='I',ylabel='Q')
        trace.record('rx.soft_bits',llr,kind='sequence',title='F3 descrambled soft scores')
        if plotter is None:trace.show()
        return dict(**result,detected=bool(detected),metric=metric,soft_bits=llr,equalized_symbols=np.array(equalized),channel_estimates=np.array(estimates),rx_grid=grid)
