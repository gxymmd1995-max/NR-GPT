import importlib.util
from pathlib import Path
import pytest


@pytest.mark.matlab
def test_actual_matlab(request):
    path=Path(__file__).resolve().parents[2]/'examples/pucch'
    if not (path/'NRPUCCH1_reference.json').exists():
        if request.config.getoption('--require-matlab'):pytest.fail('Actual F1 MATLAB reference missing')
        pytest.skip('Actual F1 MATLAB reference missing')
    spec=importlib.util.spec_from_file_location('f1compare',path/'compare_NRPUCCH1_reference.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    assert m.compare(write_report=False)['decision_mismatches']==0
