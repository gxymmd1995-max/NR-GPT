"""Real MATLAB nrUCIEncode comparison and decode actual codewords."""

import json, hashlib
from pathlib import Path
import numpy as np
from common.NRUCICode import NRUCICode


def compare(write_report=True):
    folder = Path(__file__).resolve().parent
    root = folder.parents[1]
    reference = json.loads((folder / "NRUCICode_reference.json").read_text())
    errors = []
    for c in reference["cases"]:
        codec = NRUCICode(c["A"], c["E"])
        word = codec.encode(c["bits"])
        expected = np.array(c["encoded"])
        decoded = codec.decode(20 * (1 - 2 * expected))
        errors.append(
            dict(
                A=c["A"],
                E=c["E"],
                encoded_errors=int(np.count_nonzero(word != expected)),
                decoded_errors=int(
                    np.count_nonzero(np.array(decoded["bits"]) != c["bits"])
                ),
                crc_ok=decoded["crc_ok"],
            )
        )
    paths = [
        folder / "NRUCICode_reference.json",
        folder / "export_NRUCICode_reference.m",
        Path(__file__),
    ]
    paths += [
        root / "src/common" / n
        for n in (
            "NRUCICode.py",
            "NRPolarCode.py",
            "NRSmallBlockCode.py",
            "_small_block_tables.py",
            "_coding_tables.json",
        )
    ]
    passed = all(
        c["encoded_errors"] == 0
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
        (folder / "NRUCICode_comparison.json").write_text(
            json.dumps(report, indent=2) + "\n"
        )
    assert passed, errors
    return report


if __name__ == "__main__":
    print(json.dumps(compare(), indent=2))
