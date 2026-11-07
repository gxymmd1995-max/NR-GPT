import importlib.util
from pathlib import Path
import pytest


@pytest.mark.matlab
def test_actual_pdsch_mimo(request):
    folder=Path(__file__).resolve().parents[2]/'examples/pdsch'
    if not (folder/'NRPDSCH_mimo_reference.json').exists():
        if request.config.getoption('--require-matlab'):pytest.fail('Missing actual PDSCH MIMO reference')
        pytest.skip('Missing PDSCH MIMO reference')
    spec=importlib.util.spec_from_file_location('pdschmimo',folder/'compare_NRPDSCH_mimo_reference.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    assert m.compare(write_report=False)['case_count']==64
