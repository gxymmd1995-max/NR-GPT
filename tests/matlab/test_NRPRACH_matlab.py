import importlib.util
from pathlib import Path
import pytest


@pytest.mark.matlab
def test_actual_prach_reference(request):
    folder=Path(__file__).resolve().parents[2]/'examples/prach'
    if not (folder/'NRPRACH_reference.json').exists():
        if request.config.getoption('--require-matlab'):pytest.fail('Missing actual PRACH reference')
        pytest.skip('Missing actual PRACH reference')
    spec=importlib.util.spec_from_file_location('prach_reference',folder/'compare_NRPRACH_reference.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    result=module.compare(write_report=False)
    assert result['case_count']==44 and result['sequence_case_count']==32
