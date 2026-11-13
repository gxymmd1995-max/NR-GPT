"""960组真实5G Toolbox序列/坐标、40组时域/信道/接收及Toolbox UCI对照。"""

import importlib.util
from pathlib import Path

import pytest


@pytest.mark.matlab
def test_pucch0_actual_matlab_vectors(request):
    output = Path(__file__).resolve().parents[2] / "examples/pucch"
    if not (output / "NRPUCCH0_reference.json").exists():
        if request.config.getoption("--require-matlab"):
            pytest.fail("Run actual MATLAB export_NRPUCCH0_reference.m")
        pytest.skip("Actual MATLAB PUCCH0 reference missing")
    spec = importlib.util.spec_from_file_location(
        "pucch0_reference", output / "compare_NRPUCCH0_reference.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report = module.compare(write_report=False)
    assert report["sequence_case_count"] == 960 and report["waveform_case_count"] == 40
