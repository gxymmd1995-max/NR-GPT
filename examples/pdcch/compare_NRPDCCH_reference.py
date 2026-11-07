import json,hashlib
from pathlib import Path
import numpy as np
from cell import NRCell
from pdcch import NRPDCCH,NRPDCCHTransmitter,NRPDCCHReceiver

def compare(write_report=True):
    folder=Path(__file__).resolve().parent;root=folder.parents[1]
    ref=json.loads((folder/'NRPDCCH_reference.json').read_text());cases=[]
    for c in ref['cases']:
        v=c['variant'];cell=NRCell(n_size_grid=96,n_start_grid=12,subcarrier_spacing_khz=30,n_slot=3)
        r=NRPDCCH(cell,frequency_resources=tuple(range(16)),duration=v+1,start_symbol=1,aggregation_level=c['al'],mapping_type='interleaved' if v==1 else 'noninterleaved',reg_bundle_size=2 if v==1 else 6,interleaver_size=3,shift_index=17,scrambling_id=271,scrambling_rnti=4321,dmrs_type_a_position=3)
        sent=NRPDCCHTransmitter(r,rnti=4321).transmit(c['bits'])
        grid=(np.array(c['grid_real'])+1j*np.array(c['grid_imag'])).reshape(1,14,1152)
        wave=(np.array(c['wave_real'])+1j*np.array(c['wave_imag']))[None,:]
        out=NRPDCCHReceiver(r,c['A'],rnti=4321).receive(wave)
        cases.append(dict(al=c['al'],variant=v,coding_errors=int(np.count_nonzero(sent['coded_bits']!=c['coded'])),grid_error=float(np.max(abs(grid-sent['grid'].data))),wave_error=float(np.max(abs(wave-sent['waveform']))),decoded_ok=out['bits']==c['bits'] and out['crc_ok']))
    passed=all(not c['coding_errors'] and c['grid_error']<1e-10 and c['wave_error']<1e-10 and c['decoded_ok'] for c in cases)
    paths=list((root/'src/pdcch').glob('*.py'))+[root/'src/common/NRDCICode.py',Path(__file__),folder/'NRPDCCH_reference.json',folder/'export_NRPDCCH_reference.m']
    paths += [root/'src/common'/n for n in ('NRPolarCode.py','NRUCICode.py','NRCommon.py','NROFDM.py','NRPhaseRotation.py','_validation.py','_coding_tables.json')]
    paths += [root/'src/grid/NRGrid.py',root/'src/channel/NRChannel.py']
    report=dict(status='passed' if passed else 'failed',case_count=len(cases),cases=cases,matlab_version=ref['matlab_version'],toolbox=ref['toolbox'],hashes={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    if write_report:(folder/'NRPDCCH_comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    assert passed,cases
    return report

if __name__=='__main__':
    r=compare();print(json.dumps(dict(status=r['status'],cases=r['case_count'],max_grid_error=max(c['grid_error'] for c in r['cases']),max_wave_error=max(c['wave_error'] for c in r['cases'])),indent=2))
