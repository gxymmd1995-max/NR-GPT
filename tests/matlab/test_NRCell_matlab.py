"""读取实际 MATLAB 导出的结果；缺少向量时明确跳过或失败。"""

import json
from pathlib import Path

import pytest

from cell import NRCell

REFERENCE = Path(__file__).resolve().parents[2] / "examples/cell/NRCell_reference.json"


@pytest.mark.matlab
def test_matlab_carrier_reference(request):
    if not REFERENCE.exists():
        message = "Run examples/cell/export_NRCell_reference.m using MATLAB 5G Toolbox first"
        if request.config.getoption("--require-matlab"):
            pytest.fail(message)
        pytest.skip(message)
    reference = json.loads(REFERENCE.read_text(encoding="utf-8-sig"))
    assert reference["matlab_version"]
    assert reference["toolbox"]
    assert reference["fft_policy"]
    assert len(reference["cases"]) == 78
    for case in reference["cases"]:
        cell = NRCell(**case["input"])
        for name, expected in case["expected"].items():
            actual = cell.symbols_per_slot if name == "grid_symbols" else getattr(cell, name)
            if isinstance(expected, list):
                actual = list(actual)
            assert actual == expected, (case["input"], name, actual, expected)
