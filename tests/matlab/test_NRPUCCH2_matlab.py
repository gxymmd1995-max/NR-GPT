import importlib.util
from pathlib import Path
import pytest


@pytest.mark.matlab
def test_actual_matlab(request):
    folder = Path(__file__).resolve().parents[2] / "examples/pucch"
    if not (folder / "NRPUCCH2_reference.json").exists():
        if request.config.getoption("--require-matlab"):
            pytest.fail("Export actual MATLAB F2 reference")
        pytest.skip("Actual MATLAB F2 reference missing")
    spec = importlib.util.spec_from_file_location(
        "f2compare", folder / "compare_NRPUCCH2_reference.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert m.compare(write_report=False)["case_count"] == 56
