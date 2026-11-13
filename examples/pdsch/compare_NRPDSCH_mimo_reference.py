"""Compare actual Toolbox multilayer/DMRS/MIMO waveforms and blind-to-truth channel estimates."""

import json, hashlib
from pathlib import Path
import numpy as np
from cell import NRCell
from pdsch import NRPDSCH, NRPDSCHTransmitter, NRPDSCHReceiver


def compare(write_report=True):
    folder = Path(__file__).resolve().parent
    root = folder.parents[1]
    reference = json.loads((folder / "NRPDSCH_mimo_reference.json").read_text())
    errors = []
    for c in reference["cases"]:
        cell = NRCell(
            n_cell_id=17,
            n_size_grid=6,
            n_start_grid=10,
            bwp_start=11,
            bwp_size=4,
            n_slot=3,
            n_rx_antennas=4,
        )
        ports = tuple(map(int, np.atleast_1d(c["ports"])))
        r = NRPDSCH(
            cell,
            prb=1,
            n_prbs=2,
            n_symbols=c["L"],
            rnti=4321,
            data_scrambling_id=731,
            dmrs_scrambling_id=271,
            n_scid=c["scid"],
            dmrs_type_a_position=c["position"],
            cdm_groups_without_data=c["groups"],
            modulation=c["modulation"],
            n_layers=c["layers"],
            dmrs_configuration_type=c["type"],
            dmrs_length=c["length"],
            dmrs_additional_position=c["additional"],
            dmrs_ports=ports,
        )
        sent = NRPDSCHTransmitter(r, n_ref=c["nref"]).transmit(c["bits"])
        truth = (
            (np.array(c["H_real"]) + 1j * np.array(c["H_imag"]))
            .reshape(c["layers"], 4)
            .T
        )
        grid = (np.array(c["grid_real"]) + 1j * np.array(c["grid_imag"])).reshape(
            c["layers"], 14, 72
        )
        wave = (np.array(c["wave_real"]) + 1j * np.array(c["wave_imag"])).reshape(4, -1)
        decoded = NRPDSCHReceiver(r, c["A"], n_ref=c["nref"]).receive(wave)
        errors.append(
            dict(
                layers=c["layers"],
                type=c["type"],
                length=c["length"],
                ports=list(ports),
                grid_error=float(np.max(abs(grid - sent["grid"].data))),
                wave_error=float(np.max(abs(wave - truth @ sent["waveform"]))),
                channel_error=float(
                    np.max(abs(decoded["channel_matrix"] - truth[:, :, None]))
                ),
                coding_errors=int(np.count_nonzero(sent["coded_bits"] != c["coded"])),
                decoded_errors=0 if decoded["bits"] == c["bits"] else 1,
                crc_ok=decoded["crc_ok"],
                equalizer_ok=decoded["equalizer_ok"],
            )
        )
    paths = [
        Path(__file__),
        folder / "export_NRPDSCH_mimo_reference.m",
        folder / "NRPDSCH_mimo_reference.json",
    ]
    paths += [
        root / "src/pdsch" / f"{name}.py"
        for name in ("NRPDSCH", "NRPDSCHTransmitter", "NRPDSCHReceiver")
    ]
    paths += [
        root / "src/common" / name
        for name in (
            "NRDLSCHCode.py",
            "NRULSCHCode.py",
            "NRLDPCCode.py",
            "NRCommon.py",
            "NROFDM.py",
            "NRPhaseRotation.py",
            "_qam.py",
            "_coding_tables.json",
        )
    ]
    passed = all(
        c["grid_error"] < 1e-10
        and c["wave_error"] < 1e-10
        and c["channel_error"] < 1e-10
        and c["coding_errors"] == 0
        and c["decoded_errors"] == 0
        and c["crc_ok"]
        and c["equalizer_ok"]
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
        (folder / "NRPDSCH_mimo_comparison.json").write_text(
            json.dumps(report, indent=2) + "\n"
        )
    assert passed, [
        c
        for c in errors
        if c["grid_error"] >= 1e-10
        or c["channel_error"] >= 1e-10
        or c["coding_errors"]
        or c["decoded_errors"]
        or not c["crc_ok"]
    ]
    return report


if __name__ == "__main__":
    r = compare()
    print(
        json.dumps(
            dict(
                status=r["status"],
                cases=r["case_count"],
                max_grid_error=max(c["grid_error"] for c in r["cases"]),
                max_channel_error=max(c["channel_error"] for c in r["cases"]),
            ),
            indent=2,
        )
    )
