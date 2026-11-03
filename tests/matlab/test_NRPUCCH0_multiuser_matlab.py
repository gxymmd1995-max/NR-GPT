"""独立MATLAB三用户时域叠加及逐用户候选复相关、HARQ/DTX。"""

import importlib.util
from pathlib import Path

import pytest


@pytest.mark.matlab
def test_multiuser_actual_matlab_vectors(request):
    output=Path(__file__).resolve().parents[2]/'examples/pucch'
    if not (output/'NRPUCCH0_multiuser_reference.json').exists():
        if request.config.getoption('--require-matlab'):pytest.fail('Run actual export_NRPUCCH0_multiuser_reference.m')
        pytest.skip('Actual MATLAB multiuser reference missing')
    spec=importlib.util.spec_from_file_location('multiuser_reference',output/'compare_NRPUCCH0_multiuser_reference.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    report=module.compare(write_report=False)
    assert report['case_count']==12 and report['user_result_count']==36
