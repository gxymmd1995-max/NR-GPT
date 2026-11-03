"""Compare actual MATLAB grid and full waveform, decode MATLAB waveform."""
import hashlib
import json
from pathlib import Path
import numpy as np
from cell import NRCell
from pucch import NRPUCCH1, NRPUCCH1Transmitter, NRPUCCH1Receiver


def compare(write_report=True):
    folder = Path(__file__).resolve().parent
    reference = json.loads((folder/'NRPUCCH1_reference.json').read_text())
    errors = []; mismatches = 0
    for case in reference['cases']:
        cell = NRCell(n_cell_id=17, n_size_grid=6, n_slot=3, n_rx_antennas=2)
        resource = NRPUCCH1(cell, prb=1, n_symbols=case['length'], initial_cyclic_shift=case['shift'],
            hopping_id=731, group_hopping='enable', second_hop_prb=4 if case['hopping'] else None,
            time_domain_occ=case['occ'])
        sent = NRPUCCH1Transmitter(resource).transmit(case['bits'])
        grid = (np.array(case['grid_real'])+1j*np.array(case['grid_imag'])).reshape(cell.symbols_per_slot,72)
        wave = (np.array(case['wave_real'])+1j*np.array(case['wave_imag'])).reshape(2,-1)
        predicted = np.array([.7+.4j, -.3+.6j])[:,None]*sent['waveform']
        error = max(float(np.max(abs(sent['grid'].data[0]-grid))),float(np.max(abs(predicted-wave))))
        errors.append(error)
        decoded = NRPUCCH1Receiver(resource, 2).receive(wave)
        mismatches += int(decoded['bits'] != case['bits'])
    report = dict(status='passed' if max(errors)<1e-11 and mismatches == 0 else 'failed',
                  case_count=len(errors), max_abs_error=max(errors), decision_mismatches=mismatches,
                  matlab_version=reference['matlab_version'], toolbox=reference['toolbox'])
    root = folder.parents[1]
    paths = [folder/'NRPUCCH1_reference.json', Path(__file__),folder/'export_NRPUCCH1_reference.m']
    paths += [root/'src/pucch'/f'{name}.py' for name in ('NRPUCCH1','NRPUCCH1Transmitter','NRPUCCH1Receiver')]
    report['hashes'] = {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    if write_report:
        (folder/'NRPUCCH1_comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    assert report['status'] == 'passed', report
    return report


if __name__ == '__main__':
    print(json.dumps(compare(),indent=2))
