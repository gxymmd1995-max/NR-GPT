"""Independent actual Toolbox TB coding, QAM, DMRS, OFDM and Python receive."""
import json,hashlib
from pathlib import Path
import numpy as np
from cell import NRCell
from pdsch import NRPDSCH,NRPDSCHTransmitter,NRPDSCHReceiver


def compare(write_report=True):
    folder=Path(__file__).resolve().parent;root=folder.parents[1]
    reference=json.loads((folder/'NRPDSCH_reference.json').read_text());errors=[]
    for c in reference['cases']:
        cell=NRCell(n_cell_id=17,n_size_grid=12,n_start_grid=10,bwp_start=11,bwp_size=10,n_slot=3,n_rx_antennas=2)
        r=NRPDSCH(cell,prb=1,n_prbs=8,n_symbols=12,rnti=4321,data_scrambling_id=731,dmrs_scrambling_id=271,
            n_scid=c['scid'],dmrs_type_a_position=c['position'],cdm_groups_without_data=c['groups'],modulation=c['modulation'])
        sent=NRPDSCHTransmitter(r,c['rate'],c['rv'],n_ref=c['nref']).transmit(c['bits'])
        grid=(np.array(c['grid_real'])+1j*np.array(c['grid_imag'])).reshape(14,144)
        wave=(np.array(c['wave_real'])+1j*np.array(c['wave_imag'])).reshape(2,-1)
        decoded=NRPDSCHReceiver(r,c['A'],c['rate'],c['rv'],n_ref=c['nref']).receive(wave)
        errors.append(dict(modulation=c['modulation'],rv=c['rv'],nref=c['nref'],bg=c['bg'],Z=c['Z'],
            grid_error=float(np.max(abs(grid-sent['grid'].data[0]))),
            wave_error=float(np.max(abs(wave-np.array([.7+.4j,-.3+.6j])[:,None]*sent['waveform']))),
            coding_errors=int(np.count_nonzero(sent['coded_bits']!=c['coded'])),
            decoded_errors=int(np.count_nonzero(np.array(decoded['bits'])!=c['bits'])),crc_ok=decoded['crc_ok'],converged=decoded['converged']))
    paths=[folder/'NRPDSCH_reference.json',folder/'export_NRPDSCH_reference.m',Path(__file__)]
    paths += [root/'src/pdsch'/f'{name}.py' for name in ('NRPDSCH','NRPDSCHTransmitter','NRPDSCHReceiver')]
    paths += [root/'src/common'/n for n in ('NRDLSCHCode.py','NRULSCHCode.py','_qam.py','NRLDPCCode.py','_coding_tables.json','NRCommon.py','NROFDM.py','NRPhaseRotation.py')]
    passed=all(c['grid_error']<1e-10 and c['wave_error']<1e-10 and c['coding_errors']==0 and c['decoded_errors']==0 and c['crc_ok'] and c['converged'] for c in errors)
    report=dict(status='passed' if passed else 'failed',case_count=len(errors),cases=errors,
        matlab_version=reference['matlab_version'],toolbox=reference['toolbox'],hashes={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    if write_report:(folder/'NRPDSCH_comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    assert passed,[c for c in errors if c['coding_errors'] or c['decoded_errors'] or c['grid_error']>=1e-10 or not c['crc_ok']]
    return report


if __name__=='__main__':
    r=compare();print(json.dumps(dict(status=r['status'],cases=r['case_count'],max_grid_error=max(c['grid_error'] for c in r['cases']),max_wave_error=max(c['wave_error'] for c in r['cases'])),indent=2))
