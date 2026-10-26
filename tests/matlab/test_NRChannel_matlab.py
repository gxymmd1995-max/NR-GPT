"""独立MATLAB原生TA/CFO及显式AWGN向量对照，不假设PRNG实现相同。"""

import json
from pathlib import Path

import numpy as np
import pytest

from cell import NRCell
from channel import NRChannel


@pytest.mark.matlab
def test_channel_reference(request):
    path=Path(__file__).resolve().parents[2]/"examples/channel/NRChannel_reference.json"
    if not path.exists():
        if request.config.getoption("--require-matlab"):pytest.fail("Run actual MATLAB export_NRChannel_reference")
        pytest.skip("MATLAB channel vectors missing")
    data=json.loads(path.read_text(encoding="utf-8-sig"))
    assert data["matlab_version"] and data["toolbox"] and len(data["cases"])==24
    for case in data["cases"]:
        x,e=case["input"],case["expected"];model=NRChannel(NRCell(**x["cell"]))
        shape=(x["n_branches"],x["n_samples"])
        def vector(obj,prefix):return (np.array(obj[prefix+"real"])+1j*np.array(obj[prefix+"imag"])).reshape(shape)
        wave=vector(x,"");shifted=model.timing_advance(wave,x["ta_samples"])
        np.testing.assert_array_equal(shifted,vector(e,"shift_"))
        rotated=model.frequency_offset(shifted,x["frequency_offset_hz"],x["initial_phase_rad"],x["start_sample"])
        np.testing.assert_allclose(rotated,vector(e,"rotated_"),rtol=0,atol=1e-12)
        received,noise=model.add_awgn(rotated,x["snr_db"],noise_standard=vector(x,"standard_"))
        np.testing.assert_allclose(noise,vector(e,"noise_"),rtol=0,atol=1e-15)
        np.testing.assert_allclose(received,vector(e,"received_"),rtol=0,atol=1e-12)
        assert model.ta_command_samples(x["command"],x["initial"])==e["command_samples"]
