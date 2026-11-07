"""Actual MATLAB 100MHz cases: all active RE, coded bits, waveform probes and total energy."""
import importlib.util,json,hashlib
from pathlib import Path
import numpy as np

CASES=[('pucch','NRPUCCH'+str(i)) for i in range(5)]+[('pusch','NRPUSCH'),('pdsch','NRPDSCH'),('pdcch','NRPDCCH'),('prach','NRPRACH'),('srs','NRSRS')]

def load_case(module,name):
    path=Path(__file__).resolve().parents[1]/module/(name+'_100MHz_30kHz_demo.py')
    spec=importlib.util.spec_from_file_location(name+'_100MHz_reference',path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m.run_case()

def compare(write_report=True):
    examples=Path(__file__).resolve().parents[1];root=examples.parent;results=[]
    for module,name in CASES:
        folder=examples/module;reference=folder/(name+'_100MHz_30kHz_reference.json')
        r=json.loads(reference.read_text());out=load_case(module,name);sent=out['sent']
        wi=np.asarray(r['wave_indices'],int);wave=sent['waveform'][0]
        expected=np.asarray(r['wave_real'])+1j*np.asarray(r['wave_imag'])
        wave_error=float(np.max(abs(wave[wi]-expected)))
        energy_error=float(abs(np.sum(abs(wave)**2)-r['wave_energy'])/r['wave_energy'])
        grid_error=0.;occupied_match=True
        if 'grid' in sent:
            values=sent['grid'].data.ravel();gi=np.asarray(r['grid_indices'],int)
            truth=np.asarray(r['grid_real'])+1j*np.asarray(r['grid_imag'])
            occupied_match=np.array_equal(np.flatnonzero(abs(values)>1e-14),gi)
            grid_error=float(np.max(abs(values[gi]-truth)))
        coding_errors=int(np.count_nonzero(sent['coded_bits']!=r['coded'])) if 'coded_bits' in sent else 0
        passed=bool(out['passed'] and occupied_match and coding_errors==0 and grid_error<1e-9 and wave_error<1e-10 and energy_error<1e-9 and len(wave)==r['wave_samples'])
        paths=[Path(__file__),examples/'common/export_NR100MHz_30kHz_reference.m',reference,folder/(name+'_100MHz_30kHz_demo.py')]
        paths+=list((root/'src'/module).glob('*.py'))
        paths+=[root/'src/cell/NRCell.py',root/'src/channel/NRChannel.py',root/'src/grid/NRGrid.py']
        paths+=list((root/'src/common').glob('*.py'))+list((root/'src/common').glob('*.json'))
        report=dict(channel=name,status='passed' if passed else 'failed',grid_error=grid_error,waveform_probe_error=wave_error,
            relative_energy_error=energy_error,coding_errors=coding_errors,occupied_match=bool(occupied_match),python_channel_passed=out['passed'],
            matlab_version=r['matlab_version'],toolbox=r['toolbox'],waveform_probe_count=len(wi),
            hashes={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
        if write_report:(folder/(name+'_100MHz_30kHz_comparison.json')).write_text(json.dumps(report,indent=2)+'\n')
        results.append(report)
    assert all(r['status']=='passed' for r in results),[{k:v for k,v in r.items() if k!='hashes'} for r in results if r['status']!='passed']
    return results

if __name__=='__main__':
    results=compare();print(json.dumps([{'channel':r['channel'],'status':r['status'],'grid_error':r['grid_error'],'wave_error':r['waveform_probe_error']} for r in results],indent=2))
