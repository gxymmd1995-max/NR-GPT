import importlib.util
from pathlib import Path
import pytest


@pytest.mark.matlab
def test_actual_ulsch(request):
    folder=Path(__file__).resolve().parents[2]/'examples/common'
    if not (folder/'NRULSCHCode_reference.json').exists():
        if request.config.getoption('--require-matlab'):pytest.fail('Missing actual UL-SCH reference')
        pytest.skip('Missing UL-SCH reference')
    spec=importlib.util.spec_from_file_location('ulschref',folder/'compare_NRULSCHCode_reference.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    assert m.compare(write_report=False)['case_count']==5
