"""Actual MATLAB NR mother-code vectors; decoding actual reference codewords."""

import json, hashlib
from pathlib import Path
import numpy as np
from common.NRPolarCode import NRPolarCode
from common.NRLDPCCode import NRLDPCCode
from common.NRRMCode import NRRMCode


def compare(write_report=True):
    folder = Path(__file__).resolve().parent
    root = folder.parents[1]
    reference = json.loads(
        (folder / "NRChannelCodes_reference.json").read_text(encoding="utf-8")
    )
    errors = 0
    for case in reference["cases"]:
        code = (
            NRPolarCode(case["K"], case["N"])
            if case["kind"] == "polar"
            else (
                NRLDPCCode(case["bg"], case["Z"])
                if case["kind"] == "ldpc"
                else NRRMCode(case["r"], case["m"])
            )
        )
        bits = np.atleast_1d(case["bits"])
        encoded = code.encode(bits)
        expected = np.array(case["encoded"])
        errors += int(np.count_nonzero(encoded != expected))
        result = code.decode(20 * (1 - 2 * expected))
        decoded = result["bits"] if isinstance(result, dict) else result
        errors += int(np.count_nonzero(decoded != bits))
    paths = [
        folder / "NRChannelCodes_reference.json",
        folder / "export_NRChannelCodes_reference.m",
        Path(__file__),
    ]
    paths += [
        root / "src/common" / n
        for n in (
            "NRPolarCode.py",
            "NRLDPCCode.py",
            "NRRMCode.py",
            "_coding_tables.json",
        )
    ]
    report = dict(
        status="passed" if errors == 0 else "failed",
        case_count=len(reference["cases"]),
        bit_errors=errors,
        matlab_version=reference["matlab_version"],
        toolbox=reference["toolbox"],
        hashes={
            p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in paths
        },
    )
    if write_report:
        (folder / "NRChannelCodes_comparison.json").write_text(
            json.dumps(report, indent=2) + "\n"
        )
    assert errors == 0, report
    return report


if __name__ == "__main__":
    print(json.dumps(compare(), indent=2))
