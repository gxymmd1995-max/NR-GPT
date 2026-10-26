"""全部R15矩阵与真实MATLAB nrPUSCHCodebook独立精确对照。"""

import json
from pathlib import Path

import numpy as np
import pytest

from common import NRUplinkCodebook


@pytest.mark.matlab
def test_all_r15_matrices(request):
    path = Path(__file__).resolve().parents[2]/"examples/common/NRUplinkCodebook_reference.json"
    if not path.exists():
        if request.config.getoption("--require-matlab"):
            pytest.fail("Generate actual MATLAB export_NRUplinkCodebook_reference first")
        pytest.skip("MATLAB codebook vectors unavailable")
    reference = json.loads(path.read_text(encoding="utf-8-sig"))
    assert reference["matlab_version"] and reference["toolbox"]
    assert len(reference["cases"]) == 72
    for case in reference["cases"]:
        w = NRUplinkCodebook.matrix(case["n_ports"], case["rank"], case["tpmi"])
        target = np.asarray(case["real"])+1j*np.asarray(case["imag"])
        np.testing.assert_allclose(w.ravel(), target.reshape(-1), rtol=0, atol=1e-15)
