import json,hashlib
from pathlib import Path
from dataclasses import replace
import numpy as np
from cell import NRCell
from ssb import NRSSB,NRSSBTransmitter,NRSSBReceiver

def compare(write_report=True):
    folder=Path(__file__).resolve().parent;root=folder.parents[1]
    ref=json.loads((folder/'NRSSB_reference.json').read_text());cases=[]
    for c in ref['cases']:
        cell=NRCell(n_cell_id=c['pci'],n_size_grid=c['n_size_grid'],subcarrier_spacing_khz=c['scs'])
        r=NRSSB(cell,start_subcarrier=24,l_max=c['lmax'],ssb_index=c['ssb_index'],half_frame=c['half_frame'],k_ssb=c['k_ssb'])
        sent=NRSSBTransmitter(r).transmit(c['mib'],c['sfn_lsb'])
        truth=(np.array(c['grid_real'])+1j*np.array(c['grid_imag'])).reshape(1,14,12*c['n_size_grid'])
        wave=(np.array(c['wave_real'])+1j*np.array(c['wave_imag']))[None,:]
        # Receiver geometry has an intentionally wrong PCI and index; acquisition recovers them.
        unknown=replace(r,cell=replace(cell,n_cell_id=(c['pci']+17)%1008),ssb_index=0,half_frame=0)
        out=NRSSBReceiver(unknown).receive(wave)
        cases.append(dict(pci=c['pci'],lmax=c['lmax'],half_frame=c['half_frame'],sfn_lsb=c['sfn_lsb'],
            coding_errors=int(np.count_nonzero(sent['coded_bits']!=c['coded'])),
            grid_error=float(np.max(abs(truth-sent['grid'].data))),wave_error=float(np.max(abs(wave-sent['waveform']))),
            decoded_ok=out['mib']==c['mib'] and out['crc_ok'] and out['cell_id']==c['pci'] and out['ssb_index']==c['ssb_index'] and out['sfn_lsb']==c['sfn_lsb'] and out['half_frame']==c['half_frame']))
    passed=all(not c['coding_errors'] and c['grid_error']<1e-10 and c['wave_error']<1e-10 and c['decoded_ok'] for c in cases)
    paths=list((root/'src/ssb').glob('*.py'))+[root/'src/common/NRBCHCode.py',root/'src/common/NRPolarCode.py',root/'src/common/NRUCICode.py',root/'src/common/_coding_tables.json',root/'src/common/NRCommon.py',root/'src/common/NROFDM.py',root/'src/cell/NRCell.py',Path(__file__),folder/'export_NRSSB_reference.m',folder/'NRSSB_reference.json']
    paths += [root/'src/common/NRPhaseRotation.py',root/'src/common/_validation.py',root/'src/channel/NRChannel.py',root/'src/grid/NRGrid.py']
    report=dict(status='passed' if passed else 'failed',case_count=len(cases),cases=cases,matlab_version=ref['matlab_version'],toolbox=ref['toolbox'],hashes={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    if write_report:(folder/'NRSSB_comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    assert passed,[c for c in cases if c['coding_errors'] or not c['decoded_ok'] or c['grid_error']>1e-10]
    return report

if __name__=='__main__':
    r=compare();print(json.dumps(dict(status=r['status'],cases=r['case_count'],max_grid_error=max(c['grid_error'] for c in r['cases']),max_wave_error=max(c['wave_error'] for c in r['cases'])),indent=2))
