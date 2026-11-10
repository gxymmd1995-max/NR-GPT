"""Independent actual R2024a sequence and mapping references."""
import importlib.util
from pathlib import Path
import pytest

@pytest.mark.matlab
def test_reference_signals():
    p=Path(__file__).resolve().parents[2]/'examples/common/compare_NRReferenceSignals_reference.py'
    spec=importlib.util.spec_from_file_location('reference_signals_comparison',p)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report=module.compare(False)
    assert len(report['cases'])==99 and report['passed']
