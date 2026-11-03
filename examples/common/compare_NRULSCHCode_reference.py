"""Compare actual Toolbox single-code-block UL-SCH CRC/LDPC/RV vectors."""
from pathlib import Path
import json,hashlib
import numpy as np
from common.NRULSCHCode import NRULSCHCode


def compare(write_report=True):
    folder=Path(__file__).resolve().parent;root=folder.parents[1]
    reference=json.loads((folder/'NRULSCHCode_reference.json').read_text());errors=[]
    for c in reference['cases']:
        codec=NRULSCHCode(c['A'],c['rate'],c['E'],c['qm'],c['rv'])
        coded=codec.encode(c['bits']);out=codec.decode(20*(1-2*np.array(c['coded'])))
        errors.append(dict(A=c['A'],bg=codec.base_graph,Z=codec.lifting_size,
            coding_errors=int(np.count_nonzero(coded!=c['coded'])),decoded_errors=int(np.count_nonzero(np.array(out['bits'])!=c['bits'])),
            crc_ok=out['crc_ok'],converged=out['converged']))
    paths=[Path(__file__),folder/'export_NRULSCHCode_reference.m',folder/'NRULSCHCode_reference.json']
    paths += [root/'src/common'/n for n in ('NRULSCHCode.py','NRLDPCCode.py','_coding_tables.json')]
    passed=all(c['coding_errors']==0 and c['decoded_errors']==0 and c['crc_ok'] and c['converged'] for c in errors)
    report=dict(status='passed' if passed else 'failed',case_count=len(errors),cases=errors,matlab_version=reference['matlab_version'],toolbox=reference['toolbox'],
        hashes={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    if write_report:(folder/'NRULSCHCode_comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    assert passed,errors
    return report


if __name__=='__main__':
    r=compare();print(json.dumps(dict(status=r['status'],cases=r['case_count']),indent=2))
