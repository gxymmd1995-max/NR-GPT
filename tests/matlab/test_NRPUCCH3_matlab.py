import importlib.util
from pathlib import Path
import pytest


@pytest.mark.matlab
def test_actual_f3(request):
    folder=Path(__file__).resolve().parents[2]/'examples/pucch'
    if not (folder/'NRPUCCH3_reference.json').exists():
        if request.config.getoption('--require-matlab'):pytest.fail('Missing actual F3 reference')
        pytest.skip('Missing F3 reference')
    spec=importlib.util.spec_from_file_location('f3ref',folder/'compare_NRPUCCH3_reference.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    assert m.compare(write_report=False)['case_count']==22
