"""Compare actual Toolbox reference sequences and zero-based [port,l,k] indices."""
import hashlib
import json
from pathlib import Path
import numpy as np
from cell import NRCell
from csirs import NRCSIRS
from ptrs import NRUplinkPTRS,NRDownlinkPTRS
from pusch import NRPUSCH
from pdsch import NRPDSCH

def compare(write_report=True):
    root=Path(__file__).resolve().parent
    reference=json.loads((root/'NRReferenceSignals_reference.json').read_text())
    cell=NRCell(n_size_grid=52,subcarrier_spacing_khz=30)
    results=[]
    for i,c in enumerate(reference['cases']):
        if c['kind']=='CSI':
            resource=NRCSIRS(cell,row=c['row'],density=c['density'])
        else:
            cls,shared=(NRUplinkPTRS,NRPUSCH) if c['uplink'] else (NRDownlinkPTRS,NRPDSCH)
            resource=cls(shared(cell,dmrs_configuration_type=c['dmrs_type']),c['td'],c['fd'],c['offset'])
        x=np.asarray(c['real'])+1j*np.asarray(c['imag'])
        error=float(np.max(abs(x-resource.generate())))
        equal=bool(np.array_equal(c['indices'],resource.indices()))
        results.append(dict(case=i,index_equal=equal,max_error=error,passed=equal and error<1e-12))
    report=dict(matlab_version=reference['matlab_version'],toolbox_version=reference['toolbox_version'],
                cases=results,passed=all(c['passed'] for c in results))
    paths=['src/csirs/NRCSIRS.py','src/ptrs/NRUplinkPTRS.py','src/ptrs/NRDownlinkPTRS.py','src/ptrs/_core.py',
           'examples/common/export_NRReferenceSignals_reference.m','examples/common/compare_NRReferenceSignals_reference.py',
           'examples/common/NRReferenceSignals_reference.json']
    project=root.parents[1]
    report['sha256']={p:hashlib.sha256((project/p).read_bytes()).hexdigest() for p in paths}
    if write_report:
        (root/'NRReferenceSignals_comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report

if __name__=='__main__':
    r=compare()
    print('Actual MATLAB cases:',len(r['cases']),'passed:',r['passed'])
    if not r['passed']:
        raise SystemExit(1)
