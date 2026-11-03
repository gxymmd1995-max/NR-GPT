import importlib.util
from pathlib import Path
import pytest


@pytest.mark.matlab
def test_actual_f4(request):
    folder=Path(__file__).resolve().parents[2]/'examples/pucch'
    if not (folder/'NRPUCCH4_reference.json').exists():
        if request.config.getoption('--require-matlab'):pytest.fail('Missing actual F4 reference')
        pytest.skip('Missing F4 reference')
    spec=importlib.util.spec_from_file_location('f4ref',folder/'compare_NRPUCCH4_reference.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    assert m.compare(write_report=False)['case_count']==132
