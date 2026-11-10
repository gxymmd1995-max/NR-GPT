"""Reference-only PT-RS waveform through known channel and symbol CPE."""
import numpy as np
from cell import NRCell
from grid import NRGrid
from common import NROFDM
from pusch import NRPUSCH
from ptrs import NRUplinkPTRS

def run_case(plot=False):
    cell=NRCell(n_size_grid=52,subcarrier_spacing_khz=30)
    p=NRUplinkPTRS(NRPUSCH(cell),time_density=2)
    g=NRGrid(cell,1);p.map_to_grid(g)
    # Known reference channel H=1; phase acts per OFDM symbol, not as CFO.
    phases=.03*np.arange(cell.symbols_per_slot)
    wave=NROFDM(cell).modulate(g.data*np.exp(1j*phases)[None,:,None])
    received=NROFDM(cell).demodulate(wave)
    result=p.estimate_phase(received,np.ones(1))
    assert np.allclose(result['phase_rad'],phases[result['symbols']])
    if plot:
        import matplotlib.pyplot as plt
        fig,axes=plt.subplots(1,2,figsize=(11,4),layout='constrained')
        axes[0].imshow(abs(g.data[0]).T,origin='lower',aspect='auto')
        axes[0].set(xlabel='Slot symbol',ylabel='Carrier subcarrier',title='NRUplinkPTRS REs')
        axes[1].plot(np.arange(14),phases,label='True CPE')
        axes[1].plot(result['symbols'],result['phase_rad'],'o',label='PT-RS estimate')
        axes[1].set(xlabel='Slot symbol',ylabel='Phase / rad');axes[1].legend()
        plt.show()
    return result

if __name__=='__main__':
    r=run_case(True)
    print('symbols:',r['symbols'],'phase_rad:',r['phase_rad'])
