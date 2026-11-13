import importlib.util
from pathlib import Path
import pytest


@pytest.mark.matlab
def test_actual_pdsch(request):
    folder = Path(__file__).resolve().parents[2] / "examples/pdsch"
    if not (folder / "NRPDSCH_reference.json").exists():
        if request.config.getoption("--require-matlab"):
            pytest.fail("Missing actual PDSCH reference")
        pytest.skip("Missing PDSCH reference")
    spec = importlib.util.spec_from_file_location(
        "pdschref", folder / "compare_NRPDSCH_reference.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert m.compare(write_report=False)["case_count"] == 32
