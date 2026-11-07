"""PRACH ZC -> DFT -> separate PRACH FFT grid -> IFFT, repetitions and one CP."""
from dataclasses import dataclass
import numpy as np
from common._validation import real_value
from diagnostics import NRPlotConfig, NRStagePlotter
from .NRPRACH import NRPRACH


@dataclass(frozen=True, slots=True)
class NRPRACHTransmitter:
    resource: NRPRACH
    plot_config: NRPlotConfig | None = None

    def __post_init__(self):
        if not isinstance(self.resource,NRPRACH):
            raise TypeError('resource must be NRPRACH')
        NRStagePlotter(self.plot_config)

    def transmit(self, preamble_index=0, beta=1., *, plotter=None):
        r=self.resource;beta=real_value('beta',beta,0)
        sequence=r.sequence(preamble_index);symbols=r.generate(preamble_index)
        useful=r.useful_waveform(preamble_index)
        # C2 can have CP >= one useful period; modulo indexing handles this correctly.
        prefix=useful[np.arange(-r.cp_samples,0)%r.n_fft]
        active=beta*np.concatenate((prefix,np.tile(useful,r.repetitions)))
        wave=np.zeros((1,r.waveform_samples),complex)
        wave[0,r.occasion_start_samples:r.occasion_start_samples+r.active_samples]=active
        trace=NRStagePlotter(self.plot_config) if plotter is None else plotter
        trace.record('tx.zc',sequence,kind='sequence',title='Cyclically shifted Zadoff-Chu sequence')
        trace.record('tx.dft',symbols,kind='sequence',title='Unnormalized PRACH sequence DFT')
        trace.record('tx.frequency_grid',np.fft.fftshift(r.spectrum(preamble_index))[None,None,:],kind='grid',title='Separate PRACH frequency grid')
        trace.record('tx.ifft',useful,title='One useful PRACH period before CP')
        trace.record('tx.waveform',wave,title='PRACH CP, repetitions, occasion offset and guard')
        if plotter is None: trace.show()
        logical,u,cv=r.preamble_parameters(preamble_index)
        return dict(waveform=wave,sequence=sequence,symbols=symbols,logical_root=logical,
                    root_sequence=u,cyclic_shift=cv,cp_samples=r.cp_samples,n_fft=r.n_fft)
