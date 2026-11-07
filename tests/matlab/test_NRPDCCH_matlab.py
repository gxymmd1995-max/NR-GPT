import importlib.util
from pathlib import Path
import pytest

@pytest.mark.matlab
def test_actual_pdcch(request):
    folder=Path(__file__).resolve().parents[2]/'examples/pdcch'
    if not (folder/'NRPDCCH_reference.json').exists():
        if request.config.getoption('--require-matlab'):pytest.fail('Missing actual PDCCH reference')
        pytest.skip('Missing actual PDCCH reference')
    spec=importlib.util.spec_from_file_location('pdcch_reference',folder/'compare_NRPDCCH_reference.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    assert m.compare(write_report=False)['case_count']==15
