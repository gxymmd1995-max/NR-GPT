import importlib.util
from pathlib import Path
import pytest


@pytest.mark.matlab
def test_actual_100mhz_all_channels(request):
    root = Path(__file__).resolve().parents[2]
    path = root / "examples/common/compare_NR100MHz_30kHz_reference.py"
    spec = importlib.util.spec_from_file_location("nr100mhz", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    missing = [
        name
        for module, name in m.CASES
        if not (
            root / "examples" / module / (name + "_100MHz_30kHz_reference.json")
        ).exists()
    ]
    if missing:
        if request.config.getoption("--require-matlab"):
            pytest.fail(str(missing))
        pytest.skip("Missing actual MATLAB 100MHz references")
    assert len(m.compare(write_report=False)) == 10
