"""Compare actual Toolbox UCI, QPSK/pi2-BPSK transform precoding, DMRS and waveform."""
import json,hashlib
from pathlib import Path
import numpy as np
from cell import NRCell
from pucch import NRPUCCH3,NRPUCCH3Transmitter,NRPUCCH3Receiver


def compare(write_report=True):
    folder=Path(__file__).resolve().parent;root=folder.parents[1]
    reference=json.loads((folder/'NRPUCCH3_reference.json').read_text());errors=[]
    for c in reference['cases']:
        cell=NRCell(n_cell_id=17,n_size_grid=24,n_slot=3,n_rx_antennas=2)
        r=NRPUCCH3(cell,prb=1,n_prbs=c['P'],n_symbols=c['L'],rnti=4321,data_scrambling_id=731,
            hopping_id=271,group_hopping='enable',second_hop_prb=12 if c['hop'] else None,additional_dmrs=c['extra'],modulation=c['modulation'])
        sent=NRPUCCH3Transmitter(r).transmit(c['bits'])
        grid=(np.array(c['grid_real'])+1j*np.array(c['grid_imag'])).reshape(14,288)
        wave=(np.array(c['wave_real'])+1j*np.array(c['wave_imag'])).reshape(2,-1)
        decoded=NRPUCCH3Receiver(r,c['A']).receive(wave)
        errors.append(dict(L=c['L'],P=c['P'],modulation=c['modulation'],
            grid_error=float(np.max(abs(grid-sent['grid'].data[0]))),wave_error=float(np.max(abs(wave-np.array([.7+.4j,-.3+.6j])[:,None]*sent['waveform']))),
            coding_errors=int(np.count_nonzero(sent['coded_bits']!=c['coded'])),decoded_errors=int(np.count_nonzero(np.array(decoded['bits'])!=c['bits'])),crc_ok=decoded['crc_ok']))
    paths=[folder/'NRPUCCH3_reference.json',folder/'export_NRPUCCH3_reference.m',Path(__file__)]
    paths += [root/'src/pucch'/f'{name}.py' for name in ('NRPUCCH3','NRPUCCH3Transmitter','NRPUCCH3Receiver')]
    paths += [root/'src/common'/n for n in ('NRUCICode.py','NRPolarCode.py','NRCommon.py','NROFDM.py','NRPhaseRotation.py','_low_papr_24.json')]
    passed=all(c['grid_error']<1e-10 and c['wave_error']<1e-10 and c['coding_errors']==0 and c['decoded_errors']==0 and c['crc_ok'] is not False for c in errors)
    report=dict(status='passed' if passed else 'failed',case_count=len(errors),cases=errors,matlab_version=reference['matlab_version'],toolbox=reference['toolbox'],
        hashes={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    if write_report:(folder/'NRPUCCH3_comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    assert passed,errors
    return report


if __name__=='__main__':print(json.dumps(compare(),indent=2))
