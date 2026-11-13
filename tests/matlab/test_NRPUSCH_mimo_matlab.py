import importlib.util
from pathlib import Path
import pytest


@pytest.mark.matlab
def test_actual_pusch_mimo(request):
    folder = Path(__file__).resolve().parents[2] / "examples/pusch"
    if not (folder / "NRPUSCH_mimo_reference.json").exists():
        if request.config.getoption("--require-matlab"):
            pytest.fail("Missing actual PUSCH MIMO reference")
        pytest.skip("Missing PUSCH MIMO reference")
    spec = importlib.util.spec_from_file_location(
        "puschmimo", folder / "compare_NRPUSCH_mimo_reference.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert m.compare(write_report=False)["case_count"] == 64
