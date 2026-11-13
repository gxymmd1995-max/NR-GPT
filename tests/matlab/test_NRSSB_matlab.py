import importlib.util
from pathlib import Path
import pytest


@pytest.mark.matlab
def test_actual_ssb_bch(request):
    folder = Path(__file__).resolve().parents[2] / "examples/ssb"
    if not (folder / "NRSSB_reference.json").exists():
        if request.config.getoption("--require-matlab"):
            pytest.fail("Missing actual SSB reference")
        pytest.skip("Missing actual SSB reference")
    spec = importlib.util.spec_from_file_location(
        "ssb_reference", folder / "compare_NRSSB_reference.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert m.compare(write_report=False)["case_count"] == 25
