import importlib.util
from pathlib import Path
import pytest


@pytest.mark.matlab
def test_actual_dl_sch(request):
    folder = Path(__file__).resolve().parents[2] / "examples/common"
    if not (folder / "NRDLSCHCode_reference.json").exists():
        if request.config.getoption("--require-matlab"):
            pytest.fail("Missing actual DL-SCH reference")
        pytest.skip("Missing DL-SCH reference")
    spec = importlib.util.spec_from_file_location(
        "dlschref", folder / "compare_NRDLSCHCode_reference.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert m.compare(write_report=False)["case_count"] == 5
