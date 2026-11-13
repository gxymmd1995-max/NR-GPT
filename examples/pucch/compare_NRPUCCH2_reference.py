"""Actual MATLAB UCI coding/grid/full waveform and Python receive comparison."""

import json, hashlib
from pathlib import Path
import numpy as np
from cell import NRCell
from pucch import NRPUCCH2, NRPUCCH2Transmitter, NRPUCCH2Receiver


def compare(write_report=True):
    folder = Path(__file__).resolve().parent
    root = folder.parents[1]
    reference = json.loads((folder / "NRPUCCH2_reference.json").read_text())
    errors = []
    mismatches = 0
    coding_errors = 0
    for c in reference["cases"]:
        cell = NRCell(
            n_cell_id=17,
            n_size_grid=12,
            n_start_grid=10,
            bwp_start=11,
            bwp_size=10,
            n_slot=3,
            n_rx_antennas=2,
        )
        resource = NRPUCCH2(
            cell,
            prb=1,
            n_prbs=c["P"],
            start_symbol=8,
            n_symbols=c["L"],
            rnti=4321,
            data_scrambling_id=731,
            dmrs_scrambling_id=271,
            second_hop_prb=6 if c["hop"] else None,
        )
        sent = NRPUCCH2Transmitter(resource).transmit(c["bits"])
        grid = (np.array(c["grid_real"]) + 1j * np.array(c["grid_imag"])).reshape(
            14, 144
        )
        wave = (np.array(c["wave_real"]) + 1j * np.array(c["wave_imag"])).reshape(2, -1)
        predicted = np.array([0.7 + 0.4j, -0.3 + 0.6j])[:, None] * sent["waveform"]
        errors.append(
            max(
                float(np.max(abs(sent["grid"].data[0] - grid))),
                float(np.max(abs(wave - predicted))),
            )
        )
        coding_errors += int(np.count_nonzero(sent["coded_bits"] != c["coded"]))
        result = NRPUCCH2Receiver(resource, c["A"]).receive(wave)
        mismatches += int(result["bits"] != c["bits"])
    paths = [
        folder / "NRPUCCH2_reference.json",
        folder / "export_NRPUCCH2_reference.m",
        Path(__file__),
    ]
    paths += [
        root / "src/pucch" / f"{name}.py"
        for name in ("NRPUCCH2", "NRPUCCH2Transmitter", "NRPUCCH2Receiver")
    ]
    paths += [
        root / "src/common" / name
        for name in (
            "NRSmallBlockCode.py",
            "_small_block_tables.py",
            "NRCommon.py",
            "NROFDM.py",
            "NRPhaseRotation.py",
            "NRUCICode.py",
            "NRPolarCode.py",
            "_coding_tables.json",
        )
    ]
    report = dict(
        status=(
            "passed"
            if max(errors) < 1e-11 and mismatches == 0 and coding_errors == 0
            else "failed"
        ),
        case_count=len(errors),
        max_abs_error=max(errors),
        coding_bit_errors=coding_errors,
        decision_mismatches=mismatches,
        matlab_version=reference["matlab_version"],
        toolbox=reference["toolbox"],
        hashes={
            p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in paths
        },
    )
    if write_report:
        (folder / "NRPUCCH2_comparison.json").write_text(
            json.dumps(report, indent=2) + "\n"
        )
    assert report["status"] == "passed", report
    return report


if __name__ == "__main__":
    print(json.dumps(compare(), indent=2))
