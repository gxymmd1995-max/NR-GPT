"""逐个比较 MATLAB 实测 SRS 复数向量、坐标、u/v/alpha、k0/n_b 和映射网格。"""

import json
from pathlib import Path

import numpy as np
import pytest

from cell import NRCell
from grid import NRGrid
from srs import NRSRS

REFERENCE = Path(__file__).resolve().parents[2] / "examples/srs/NRSRS_reference.json"


@pytest.mark.matlab
def test_matlab_srs_reference(request):
    if not REFERENCE.exists():
        message = "Run examples/srs/export_NRSRS_reference.m using MATLAB 5G Toolbox first"
        if request.config.getoption("--require-matlab"):
            pytest.fail(message)
        pytest.skip(message)
    reference = json.loads(REFERENCE.read_text(encoding="utf-8-sig"))
    assert reference["matlab_version"] and reference["toolbox"]
    assert len(reference["cases"]) == 832
    for case_id, case in enumerate(reference["cases"]):
        x = case["input"].copy()
        cell = NRCell(**x.pop("cell"))
        srs = NRSRS(cell, **x)
        e = case["expected"]
        context = f"MATLAB case {case_id}: {x}, cell={cell}"
        indices = srs.indices()
        np.testing.assert_array_equal(indices, np.asarray(e["indices"], dtype=np.int64).reshape(-1, 3), err_msg=context)
        symbols = srs.generate()
        assert srs.is_active == e["active"], context
        assert list(symbols.shape) == e["sequence_shape"], context
        expected = np.asarray(e["symbols_real"]) + 1j * np.asarray(e["symbols_imag"])
        # MATLAB 直接计算大 ZC 相位，Python 先模 2π；宽带向量允许 2e-9 的舍入差。
        np.testing.assert_allclose(symbols.ravel(order="F"), expected, rtol=0, atol=2e-9, err_msg=context)
        if srs.is_active:
            params = srs.sequence_parameters()
            np.testing.assert_array_equal(params["u"], np.atleast_1d(e["seq_group"]), err_msg=context)
            np.testing.assert_array_equal(params["v"], np.atleast_1d(e["n_seq"]), err_msg=context)
            np.testing.assert_allclose(params["alpha"], np.atleast_1d(e["alpha"]), rtol=0, atol=1e-14, err_msg=context)
            assert srs.sequence_length == e["sequence_length"], context
            nb, k0 = srs._frequency_indices()
            np.testing.assert_array_equal(k0, np.asarray(e["k0"]).reshape(srs.n_ports, srs.n_symbols), err_msg=context)
            np.testing.assert_array_equal(nb, np.asarray(e["frequency_indices"]).reshape(srs.b_srs + 1, srs.n_symbols), err_msg=context)
        grid = NRGrid(cell, srs.n_ports)
        assert srs.map_to_grid(grid) == e["occupied_re_count"], context
        np.testing.assert_allclose(grid.extract(indices), expected / np.sqrt(srs.n_ports), rtol=0, atol=2e-9, err_msg=context)
        flat = grid.to_matlab().ravel(order="F")
        weights = np.arange(1, flat.size + 1)
        np.testing.assert_allclose(np.vdot(flat, flat).real, e["grid_energy"], rtol=1e-12, atol=1e-10, err_msg=context)
        # 位置加权将单点舍入误差放大；以逐点 2e-9 上界线性传播，避免任意放宽阈值。
        occupied_weights = 1 + indices[:, 2] + cell.n_subcarriers * (
            indices[:, 1] + cell.symbols_per_slot * indices[:, 0])
        bound = 2e-9 * occupied_weights.sum() / np.sqrt(srs.n_ports) + 1e-8
        np.testing.assert_allclose([flat.real @ weights, flat.imag @ weights],
                                   [e["grid_weighted_real"], e["grid_weighted_imag"]],
                                   rtol=0, atol=bound, err_msg=context)
