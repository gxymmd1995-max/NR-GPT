import importlib.util
from pathlib import Path
import pytest


@pytest.mark.matlab
def test_actual_vectors(request):
    folder = Path(__file__).resolve().parents[2] / "examples/common"
    if not (folder / "NRChannelCodes_reference.json").exists():
        if request.config.getoption("--require-matlab"):
            pytest.fail("Missing actual MATLAB code reference")
        pytest.skip("Missing MATLAB reference")
    spec = importlib.util.spec_from_file_location(
        "codes", folder / "compare_NRChannelCodes_reference.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert m.compare(write_report=False)["bit_errors"] == 0
