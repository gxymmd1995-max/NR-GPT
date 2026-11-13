"""Compare actual Toolbox reference sequences and zero-based [port,l,k] indices."""

import hashlib
import json
from pathlib import Path
import numpy as np
from cell import NRCell
from csirs import NRCSIRS
from ptrs import NRUplinkPTRS, NRDownlinkPTRS
from pusch import NRPUSCH
from pdsch import NRPDSCH


def compare(write_report=True):
    root = Path(__file__).resolve().parent
    reference = json.loads((root / "NRReferenceSignals_reference.json").read_text())
    results = []
    for i, c in enumerate(reference["cases"]):
        cell = NRCell(
            n_size_grid=c.get("grid_size", 52),
            subcarrier_spacing_khz=30,
            n_start_grid=c.get("grid_start", 0),
            n_slot=c.get("slot", 0),
            bwp_start=c.get("bwp_start"),
            bwp_size=c.get("bwp_size"),
        )
        shared_case = c["kind"] == "shared"
        if c["kind"] == "CSI":
            resource = NRCSIRS(
                cell,
                row=c["row"],
                density=c["density"],
                rb_parity=c.get("parity", 0),
                start_rb=c.get("start_rb", 0),
                n_rbs=c.get("n_rbs", 24),
                symbol=c.get("symbol", 4),
                subcarrier=c.get("subcarrier", 0),
                scrambling_id=c.get("nid", 0),
            )
        else:
            cls, shared = (
                (NRUplinkPTRS, NRPUSCH) if c["uplink"] else (NRDownlinkPTRS, NRPDSCH)
            )
            allocation = shared(
                cell,
                prb=c.get("prb", 0),
                n_prbs=c.get("n_prbs", 4),
                start_symbol=c.get("start_symbol", 0),
                n_symbols=c.get("n_symbols", 14),
                rnti=c.get("rnti", 1),
                dmrs_type_a_position=c.get("dmrs_pos", 2),
                dmrs_configuration_type=c["dmrs_type"],
                dmrs_additional_position=c.get("dmrs_additional", 0),
                dmrs_scrambling_id=c.get("nid"),
                n_scid=c.get("n_scid", 0),
                cdm_groups_without_data=c.get("cdm_groups"),
                data_scrambling_id=c.get("data_nid"),
                ptrs_config=(c["td"], c["fd"], c["offset"]) if shared_case else None,
            )
            resource = cls(allocation, c["td"], c["fd"], c["offset"])
        x = np.asarray(c["real"]) + 1j * np.asarray(c["imag"])
        generated = resource.generate()
        error = (
            float(np.max(abs(x - generated), initial=0))
            if x.shape == generated.shape
            else None
        )
        equal = bool(np.array_equal(c["indices"], resource.indices()))
        result = dict(
            case=i,
            index_equal=equal,
            max_error=error,
            passed=equal and error is not None and error < 1e-12,
        )
        if shared_case:
            data_index_equal = bool(
                np.array_equal(c["data_indices"], allocation.indices())
            )
            coded_length_equal = c["G"] == allocation.coded_length
            data_error = None
            if coded_length_equal:
                data = allocation.generate(c["bits"])
                expected = np.asarray(c["data_real"]) + 1j * np.asarray(c["data_imag"])
                data_error = float(np.max(abs(data - expected)))
            result.update(
                data_index_equal=data_index_equal,
                coded_length_equal=coded_length_equal,
                data_max_error=data_error,
                passed=result["passed"]
                and data_index_equal
                and coded_length_equal
                and data_error < 1e-12,
            )
        results.append(result)
    report = dict(
        matlab_version=reference["matlab_version"],
        toolbox_version=reference["toolbox_version"],
        cases=results,
        passed=all(c["passed"] for c in results),
    )
    paths = [
        "src/csirs/NRCSIRS.py",
        "src/ptrs/NRUplinkPTRS.py",
        "src/ptrs/NRDownlinkPTRS.py",
        "src/ptrs/_core.py",
        "src/pdsch/NRPDSCH.py",
        "src/pusch/NRPUSCH.py",
        "examples/common/export_NRReferenceSignals_reference.m",
        "examples/common/compare_NRReferenceSignals_reference.py",
        "examples/common/NRReferenceSignals_reference.json",
    ]
    project = root.parents[1]
    report["sha256"] = {
        p: hashlib.sha256((project / p).read_bytes()).hexdigest() for p in paths
    }
    if write_report:
        (root / "NRReferenceSignals_comparison.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
    return report


if __name__ == "__main__":
    r = compare()
    print("Actual MATLAB cases:", len(r["cases"]), "passed:", r["passed"])
    if not r["passed"]:
        raise SystemExit(1)
