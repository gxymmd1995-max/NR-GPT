"""SRS接收机对比MATLAB实测输入及独立LS/噪声/时延/RI/TPMI。"""

import json
from pathlib import Path

import numpy as np
import pytest

from cell import NRCell
from srs import NRSRS, NRSRSReceiver


@pytest.mark.matlab
def test_receiver_reference(request):
    path = Path(__file__).resolve().parents[2]/"examples/srs/NRSRSReceiver_reference.json"
    if not path.exists():
        if request.config.getoption("--require-matlab"):
            pytest.fail("Generate actual MATLAB export_NRSRSReceiver_reference first")
        pytest.skip("MATLAB receiver vectors unavailable")
    reference = json.loads(path.read_text(encoding="utf-8-sig"))
    assert reference["matlab_version"] and reference["toolbox"]
    assert len(reference["cases"]) == 24
    for case_id, case in enumerate(reference["cases"]):
        x, e = case["input"], case["expected"]
        cell = NRCell(**x["cell"])
        configs = x["resources"] if isinstance(x["resources"], list) else [x["resources"]]
        resources, betas = {}, {}
        for config in configs:
            cfg = config.copy()
            uid, beta = cfg.pop("uid"), cfg.pop("beta")
            resources[uid] = NRSRS(cell, **cfg)
            betas[uid] = beta
        rx = (np.array(x["rx_real"])+1j*np.array(x["rx_imag"])).reshape(cell.n_rx_antennas,cell.symbols_per_slot,cell.n_subcarriers)
        mask = np.asarray(x["noise_mask"], dtype=bool).reshape(rx.shape[1:]) if x["explicit_noise_mask"] else None
        result = NRSRSReceiver(cell,x["n_delay_taps"]).estimate(rx, resources, noise_mask=mask, betas=betas)
        context = f"MATLAB receiver case {case_id}"
        assert result["noise"]["method"] == e["noise_method"]
        np.testing.assert_allclose(result["noise"]["wideband_noise_power_per_rx"], e["wide_per_rx"], atol=1e-10,rtol=1e-7,err_msg=context)
        target = np.asarray(e["narrow_per_rx"], dtype=float).reshape(cell.n_rx_antennas,cell.n_size_grid)
        np.testing.assert_allclose(result["noise"]["narrowband_noise_power_per_rx"],target,atol=1e-10,rtol=1e-7,equal_nan=True,err_msg=context)
        np.testing.assert_array_equal(result["noise"]["narrowband_re_count"],e["counts"])
        np.testing.assert_allclose(result["design_condition_number"],e["condition_number"],rtol=1e-7,err_msg=context)
        expected_users = e["users"] if isinstance(e["users"],list) else [e["users"]]
        for target in expected_users:
            user = result["users"][target["uid"]]
            assert user["delay_samples"] == target["delay_samples"],context
            assert user["first_path_delay_samples"] == target["first_path_delay_samples"],context
            assert user["ri"] == target["ri"] and user["tpmi"] == target["tpmi"],context
            cir = np.asarray(target["cir_real"])+1j*np.asarray(target["cir_imag"])
            h = np.asarray(target["channel_real"])+1j*np.asarray(target["channel_imag"])
            np.testing.assert_allclose(user["cir"].ravel(),cir,atol=2e-7,rtol=1e-6,err_msg=context)
            np.testing.assert_allclose(user["channel"].ravel(),h,atol=2e-7,rtol=1e-6,err_msg=context)
            for metric in ("rssi","rssi_db","rsrp","rsrp_db","snr_db","rssi_per_rx","rsrp_per_rx"):
                np.testing.assert_allclose(user[metric],target[metric],atol=2e-6,rtol=1e-6,err_msg=context)
            np.testing.assert_allclose([user["signal_power"],user["mean_delay_samples"],user["selection"]["score_bps_hz"]],
                [target["signal_power"],target["mean_delay_samples"],target["score"]],atol=2e-6,rtol=1e-6,err_msg=context)
