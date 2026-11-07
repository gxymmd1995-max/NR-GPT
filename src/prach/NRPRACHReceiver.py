"""Project PRACH receiver: known-CFO correction, repeated-period averaging, FFT matched filters."""
from dataclasses import dataclass
import numpy as np
from common.NRCommon import _integer
from common._validation import real_value, waveform_array
from channel import NRChannel
from diagnostics import NRPlotConfig, NRStagePlotter
from .NRPRACH import NRPRACH


@dataclass(frozen=True, slots=True)
class NRPRACHReceiver:
    resource: NRPRACH
    preamble_indices: tuple[int,...] = tuple(range(64))
    max_delay_samples: int = 16
    detection_threshold: float = .2
    plot_config: NRPlotConfig | None = None

    def __post_init__(self):
        if not isinstance(self.resource,NRPRACH):
            raise TypeError('resource must be NRPRACH')
        if not isinstance(self.preamble_indices,tuple) or not self.preamble_indices or len(set(self.preamble_indices))!=len(self.preamble_indices):
            raise ValueError('preamble_indices must be a nonempty unique tuple')
        for i in self.preamble_indices: _integer('preamble_index',i,0,63)
        r=self.resource
        _integer('max_delay_samples',self.max_delay_samples,0,min(r.cp_samples,r.n_fft-1))
        # A delay window spanning adjacent cyclic shifts makes user/propagation delay ambiguous.
        if r.n_cs and self.max_delay_samples>=r.n_cs*r.n_fft/r.sequence_length:
            raise ValueError('delay search must be shorter than the cyclic-shift separation')
        real_value('detection_threshold',self.detection_threshold,0,1)
        NRStagePlotter(self.plot_config)

    def receive(self, waveform, *, known_frequency_offset_hz=0., known_initial_phase_rad=0., plotter=None):
        r=self.resource;y=waveform_array(waveform)
        if y.shape!=(r.cell.n_rx_antennas,r.waveform_samples):
            raise ValueError('waveform must match [cell.n_rx_antennas, resource.waveform_samples]')
        y=NRChannel(r.cell).frequency_offset(y,-real_value('CFO',known_frequency_offset_hz),-real_value('phase',known_initial_phase_rad))
        first=r.occasion_start_samples+r.cp_samples
        periods=y[:,first:first+r.repetitions*r.n_fft].reshape(y.shape[0],r.repetitions,r.n_fft)
        # Coherent across repetitions; noncoherent across arbitrary receive-antenna phases.
        averaged=periods.mean(axis=1);spectrum=np.fft.fft(averaged,axis=1)
        energy=float(np.sum(abs(averaged)**2));profiles=[];results=[]
        for index in self.preamble_indices:
            template=r.useful_waveform(index);et=float(np.sum(abs(template)**2))
            corr=np.fft.ifft(spectrum*np.conj(np.fft.fft(template))[None,:],axis=1)
            scores=np.sum(abs(corr[:,:self.max_delay_samples+1])**2,axis=0)
            profile=np.clip(scores/(et*energy),0,1) if energy>0 else np.zeros_like(scores)
            delay=int(np.argmax(profile));metric=float(profile[delay]);profiles.append(profile)
            detected=metric>self.detection_threshold and energy>1e-20
            results.append(dict(preamble_index=index,detected=detected,metric=metric,
                delay_samples=delay if detected else None,
                delay_seconds=delay/r.cell.sample_rate_hz if detected else None,
                delay_tc=delay*r.cell.tc_per_sample if detected else None,
                channel_estimates=corr[:,delay]/et if detected else None))
        profiles=np.array(profiles);best=int(np.argmax([v['metric'] for v in results]))
        trace=NRStagePlotter(self.plot_config) if plotter is None else plotter
        trace.record('rx.average',averaged,title='Coherently averaged useful PRACH periods')
        trace.record('rx.frequency',spectrum,kind='sequence',title='Received PRACH FFT')
        trace.record('rx.delay_profiles',profiles,kind='sequence',title='Normalized preamble correlation over nonnegative sample delays',branch_prefix='Preamble')
        trace.record('rx.metrics',[v['metric'] for v in results],kind='metric',title='Preamble detection metrics',labels=[str(i) for i in self.preamble_indices])
        if plotter is None: trace.show()
        detected=[v for v in results if v['detected']]
        return dict(detected=bool(detected),detections=detected,candidates=results,
                    best_preamble_index=results[best]['preamble_index'] if detected else None,
                    delay_profiles=profiles,delay_axis_samples=np.arange(self.max_delay_samples+1))
