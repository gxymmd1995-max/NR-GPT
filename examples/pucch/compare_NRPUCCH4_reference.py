"""Compare actual MATLAB F4 UCI coding, OCC/DFT data, DMRS and time waveform."""

import json, hashlib
from pathlib import Path
import numpy as np
from cell import NRCell
from pucch import NRPUCCH4, NRPUCCH4Transmitter, NRPUCCH4Receiver


def compare(write_report=True):
    folder = Path(__file__).resolve().parent
    root = folder.parents[1]
    reference = json.loads((folder / "NRPUCCH4_reference.json").read_text())
    errors = []
    for c in reference["cases"]:
        cell = NRCell(
            n_cell_id=17,
            n_size_grid=6,
            n_start_grid=10,
            bwp_start=11,
            bwp_size=4,
            n_slot=3,
            n_rx_antennas=2,
        )
        r = NRPUCCH4(
            cell,
            prb=1,
            n_symbols=c["L"],
            rnti=4321,
            data_scrambling_id=731,
            hopping_id=271,
            group_hopping="enable",
            second_hop_prb=3 if c["hop"] else None,
            additional_dmrs=c["extra"],
            modulation=c["modulation"],
            spreading_factor=c["sf"],
            occ_index=c["occ"],
        )
        sent = NRPUCCH4Transmitter(r).transmit(c["bits"])
        grid = (np.array(c["grid_real"]) + 1j * np.array(c["grid_imag"])).reshape(
            14, 72
        )
        wave = (np.array(c["wave_real"]) + 1j * np.array(c["wave_imag"])).reshape(2, -1)
        decoded = NRPUCCH4Receiver(r, c["A"]).receive(wave)
        errors.append(
            dict(
                L=c["L"],
                sf=c["sf"],
                occ=c["occ"],
                modulation=c["modulation"],
                grid_error=float(np.max(abs(grid - sent["grid"].data[0]))),
                wave_error=float(
                    np.max(
                        abs(
                            wave
                            - np.array([0.7 + 0.4j, -0.3 + 0.6j])[:, None]
                            * sent["waveform"]
                        )
                    )
                ),
                coding_errors=int(np.count_nonzero(sent["coded_bits"] != c["coded"])),
                decoded_errors=int(
                    np.count_nonzero(np.array(decoded["bits"]) != c["bits"])
                ),
                crc_ok=decoded["crc_ok"],
            )
        )
    paths = [
        folder / "NRPUCCH4_reference.json",
        folder / "export_NRPUCCH4_reference.m",
        Path(__file__),
    ]
    paths += [
        root / "src/pucch" / f"{name}.py"
        for name in (
            "NRPUCCH4",
            "NRPUCCH4Transmitter",
            "NRPUCCH4Receiver",
            "NRPUCCH3",
            "NRPUCCH2",
        )
    ]
    paths += [
        root / "src/common" / n
        for n in (
            "NRUCICode.py",
            "NRPolarCode.py",
            "NRSmallBlockCode.py",
            "NRCommon.py",
            "NROFDM.py",
            "NRPhaseRotation.py",
            "_coding_tables.json",
            "_small_block_tables.py",
            "_low_papr_tables.py",
        )
    ]
    passed = all(
        c["grid_error"] < 1e-10
        and c["wave_error"] < 1e-10
        and c["coding_errors"] == 0
        and c["decoded_errors"] == 0
        and c["crc_ok"] is not False
        for c in errors
    )
    report = dict(
        status="passed" if passed else "failed",
        case_count=len(errors),
        cases=errors,
        matlab_version=reference["matlab_version"],
        toolbox=reference["toolbox"],
        hashes={
            p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in paths
        },
    )
    if write_report:
        (folder / "NRPUCCH4_comparison.json").write_text(
            json.dumps(report, indent=2) + "\n"
        )
    assert passed, [
        c
        for c in errors
        if c["grid_error"] >= 1e-10
        or c["decoded_errors"]
        or c["coding_errors"]
        or c["crc_ok"] is False
    ]
    return report


if __name__ == "__main__":
    report = compare()
    print(
        json.dumps(
            dict(
                status=report["status"],
                case_count=report["case_count"],
                max_grid_error=max(c["grid_error"] for c in report["cases"]),
                max_wave_error=max(c["wave_error"] for c in report["cases"]),
            ),
            indent=2,
        )
    )
