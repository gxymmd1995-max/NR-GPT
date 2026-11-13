"""实际MATLAB OFDM波形、逐符号相位以及扰动输入解调的全向量对照。"""

import json
from pathlib import Path

import numpy as np
import pytest

from cell import NRCell
from common import NROFDM, NRPhaseRotation


@pytest.mark.matlab
def test_ofdm_phase_reference(request):
    path = Path(__file__).resolve().parents[2] / "examples/common/NROFDM_reference.json"
    if not path.exists():
        if request.config.getoption("--require-matlab"):
            pytest.fail("Run actual MATLAB export_NROFDM_reference")
        pytest.skip("MATLAB OFDM vectors missing")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    assert data["matlab_version"] and data["toolbox"] and len(data["cases"]) == 28
    for case_id, case in enumerate(data["cases"]):
        x, e = case["input"], case["expected"]
        cell = NRCell(**x["cell"])
        p = x["n_branches"]
        model = NROFDM(cell, x["carrier_frequency_hz"])
        grid = (np.array(x["grid_real"]) + 1j * np.array(x["grid_imag"])).reshape(
            p, cell.symbols_per_slot, cell.n_subcarriers
        )
        target = (np.array(e["wave_real"]) + 1j * np.array(e["wave_imag"])).reshape(
            p, e["n_samples"]
        )
        np.testing.assert_allclose(
            model.modulate(grid),
            target,
            rtol=0,
            atol=2e-9,
            err_msg=f"wave case{case_id}",
        )
        np.testing.assert_allclose(
            NRPhaseRotation(cell, x["carrier_frequency_hz"]).symbol_phases(),
            e["symbol_phases"],
            rtol=0,
            atol=2e-8,
        )
        np.testing.assert_array_equal(cell.slot_cp_lengths_samples, e["cp_lengths"])
        probe = (np.array(x["probe_real"]) + 1j * np.array(x["probe_imag"])).reshape(
            target.shape
        )
        for item in e["demod"]:
            expected = (np.array(item["real"]) + 1j * np.array(item["imag"])).reshape(
                grid.shape
            )
            np.testing.assert_allclose(
                model.demodulate(probe, item["cp_fraction"]),
                expected,
                rtol=0,
                atol=3e-8,
                err_msg=f"demod case{case_id}",
            )
