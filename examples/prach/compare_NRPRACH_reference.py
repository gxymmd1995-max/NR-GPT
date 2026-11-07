"""Actual MATLAB PRACH symbols, OFDM and independent Python detection comparison."""
import hashlib
import json
from pathlib import Path
import numpy as np
from cell import NRCell
from prach import NRPRACH,NRPRACHTransmitter,NRPRACHReceiver


def compare(write_report=True):
    folder=Path(__file__).resolve().parent;root=folder.parents[1]
    reference=json.loads((folder/'NRPRACH_reference.json').read_text());cases=[];edges=[]
    for c in reference['cases']:
        cell=NRCell(n_size_grid=c['n_size'],subcarrier_spacing_khz=c['cell_scs'],duplex_mode='TDD' if c['frequency_range']=='FR2' else 'FDD')
        assert cell.sample_rate_hz==c['sample_rate']
        r=NRPRACH(cell,preamble_format=c['format'],subcarrier_spacing_khz=c['ra_scs'],
            root_sequence_index=c['root'],zero_correlation_zone=c['zcz'],frequency_start=c['frequency_start'],occasion_start_samples=c['start'],time_origin_samples=c['time_origin'])
        sent=NRPRACHTransmitter(r).transmit(c['preamble'])
        symbols=np.array(c['symbols_real'])+1j*np.array(c['symbols_imag'])
        wave=np.array(c['wave_real'])+1j*np.array(c['wave_imag'])
        # C2 Toolbox treats one full CP period as a grid symbol. Compare identical complete samples.
        assert r.cp_samples==c['cp']+(c['repetitions']-r.repetitions)*r.n_fft
        assert r.n_fft==c['fft'] and len(wave)==r.active_samples
        observed=np.zeros_like(sent['waveform']);observed[0,c['start']:]=wave
        decoded=NRPRACHReceiver(r,max_delay_samples=0).receive(observed)
        info=c['sequence_info'];_,u,cv=r.preamble_parameters(c['preamble'])
        cases.append(dict(format=c['format'],ra_scs=c['ra_scs'],ul_scs=c['cell_scs'],
            preamble=c['preamble'],sequence_error=float(np.max(abs(symbols-np.tile(sent['symbols'],c['repetitions'])))),
            waveform_error=float(np.max(abs(wave-sent['waveform'][0,c['start']:]))),
            parameter_match=u==info['RootSequence'] and cv==info['CyclicShift'] and r.n_cs==info['NumCyclicShifts'],
            detected=decoded['best_preamble_index']==c['preamble'] and len(decoded['detections'])==1 and decoded['detections'][0]['delay_samples']==0))
    for c in reference['sequence_cases']:
        r=NRPRACH(NRCell(n_size_grid=52),preamble_format=c['format'],subcarrier_spacing_khz=c['ra_scs'],
            root_sequence_index=c['root'],zero_correlation_zone=c['zcz'])
        symbols=np.array(c['symbols_real'])+1j*np.array(c['symbols_imag'])
        _,u,cv=r.preamble_parameters(c['preamble']);info=c['sequence_info']
        edges.append(dict(format=c['format'],zcz=c['zcz'],sequence_error=float(np.max(abs(symbols-np.tile(r.generate(c['preamble']),len(symbols)//r.sequence_length)))),
            parameter_match=u==info['RootSequence'] and cv==info['CyclicShift'] and r.n_cs==info['NumCyclicShifts']))
    # DFT is unnormalized (sqrt(L) magnitude); tolerance allows Toolbox large-angle ZC rounding.
    passed=all(c['sequence_error']<1e-7 and c['parameter_match'] for c in cases+edges) and all(c['waveform_error']<1e-10 and c['detected'] for c in cases)
    paths=[Path(__file__),folder/'export_NRPRACH_reference.m',folder/'NRPRACH_reference.json']
    paths+=list((root/'src/prach').glob('*.py'))+[root/'src/prach/_root_table.json',root/'src/cell/NRCell.py',root/'src/channel/NRChannel.py']
    report=dict(status='passed' if passed else 'failed',case_count=len(cases),sequence_case_count=len(edges),cases=cases,sequence_cases=edges,
        matlab_version=reference['matlab_version'],toolbox=reference['toolbox'],sequence_tolerance=1e-7,waveform_tolerance=1e-10,
        hashes={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    if write_report:(folder/'NRPRACH_comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    assert passed,[(c['format'],c['sequence_error'],c.get('waveform_error'),c['parameter_match']) for c in cases+edges if c['sequence_error']>=1e-7 or not c['parameter_match'] or c.get('waveform_error',0)>=1e-10 or not c.get('detected',True)]
    return report


if __name__=='__main__':
    r=compare();print(json.dumps(dict(status=r['status'],cases=r['case_count'],sequence_cases=r['sequence_case_count'],
        max_sequence_error=max(c['sequence_error'] for c in r['cases']+r['sequence_cases']),max_waveform_error=max(c['waveform_error'] for c in r['cases'])),indent=2))
