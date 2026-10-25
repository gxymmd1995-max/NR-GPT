"""读取真实 MATLAB 参考，重新计算 Python 序列/网格并保存比较报告。"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform

import numpy as np

from cell import NRCell
from diagnostics import ExampleLogger
from grid import NRGrid
from srs import NRSRS


def compare(log: ExampleLogger) -> dict[str, object]:
    """逐点验证全部复数值及坐标；任一不一致立即失败，不输出成功报告。"""
    output = Path(__file__).resolve().parent
    path = output / "NRSRS_reference.json"
    reference = json.loads(path.read_text(encoding="utf-8-sig"))
    results = []
    for case_id, case in enumerate(reference["cases"]):
        config = case["input"].copy()
        resource = NRSRS(NRCell(**config.pop("cell")), **config)
        expected = case["expected"]
        actual_indices = resource.indices()
        np.testing.assert_array_equal(actual_indices,
                                      np.asarray(expected["indices"], dtype=np.int64).reshape(-1, 3))
        raw = resource.generate().ravel(order="F")
        target = np.asarray(expected["symbols_real"]) + 1j*np.asarray(expected["symbols_imag"])
        np.testing.assert_allclose(raw, target, rtol=0, atol=2e-9)
        grid = NRGrid(resource.cell, resource.n_ports)
        assert resource.map_to_grid(grid) == expected["occupied_re_count"]
        grid_error = np.abs(grid.extract(actual_indices) - target/np.sqrt(resource.n_ports))
        np.testing.assert_allclose(grid.extract(actual_indices), target/np.sqrt(resource.n_ports), rtol=0, atol=2e-9)
        results.append({"case_id_0based": case_id, "active": resource.is_active,
                        "complex_value_count": int(raw.size), "index_mismatch_count": 0,
                        "max_symbol_abs_error": float(np.max(np.abs(raw-target), initial=0)),
                        "max_grid_value_abs_error": float(np.max(grid_error, initial=0))})
    report = {"status": "passed", "generated_at": datetime.now(timezone.utc).isoformat(),
              "reference_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
              "implementation_sha256": hashlib.sha256((output.parents[1]/"src/srs/NRSRS.py").read_bytes()).hexdigest(),
              "common_implementation_sha256": hashlib.sha256((output.parents[1]/"src/common/NRCommon.py").read_bytes()).hexdigest(),
              "spec_baseline": reference["spec_baseline"], "matlab_version": reference["matlab_version"],
              "toolbox": reference["toolbox"], "python_version": platform.python_version(),
              "numpy_version": np.__version__, "case_count": len(results),
              "complex_value_count": sum(item["complex_value_count"] for item in results),
              "index_mismatch_count": 0, "pointwise_rtol": 0, "pointwise_atol": 2e-9,
              "max_symbol_abs_error": max(item["max_symbol_abs_error"] for item in results),
              "max_grid_value_abs_error": max(item["max_grid_value_abs_error"] for item in results),
              "note": "Reference vectors originate in MATLAB; this report is a Python comparison, not MATLAB output. "
                      "Additional u/v/alpha/k0/n_b/energy/weighted-grid assertions run in tests/matlab/test_NRSRS_matlab.py.",
              "cases": results}
    (output/"NRSRS_comparison.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    log.logger.info("PASS: %d cases, %d complex values, zero coordinate mismatches, max error %.12g",
                    report["case_count"], report["complex_value_count"], report["max_symbol_abs_error"])
    return report


if __name__ == "__main__":
    with ExampleLogger(__file__) as run:
        compare(run)
