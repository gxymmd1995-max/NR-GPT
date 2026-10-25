"""比较 MATLAB 的真实 nrResourceGrid、sub2ind 和复数映射结果。"""

import json
from pathlib import Path

import numpy as np
import pytest

from cell import NRCell
from grid import NRGrid

REFERENCE = Path(__file__).resolve().parents[2] / "examples/grid/NRGrid_reference.json"


@pytest.mark.matlab
def test_matlab_grid_reference(request):
    if not REFERENCE.exists():
        message = "Run examples/grid/export_NRGrid_reference.m using MATLAB 5G Toolbox first"
        if request.config.getoption("--require-matlab"):
            pytest.fail(message)
        pytest.skip(message)
    reference = json.loads(REFERENCE.read_text(encoding="utf-8-sig"))
    assert reference["matlab_version"] and reference["toolbox"]
    assert len(reference["cases"]) == 18
    for case in reference["cases"]:
        selection, expected = case["selection"], case["expected"]
        grid = NRGrid(NRCell(**case["input"]), selection["n_ports"])
        # MATLAB 将单元素向量编码为标量，入口统一还原一维选择。
        indices = grid.bwp_indices(np.atleast_1d(selection["prbs"]), np.atleast_1d(selection["symbols"]),
                                   np.atleast_1d(selection["ports"]))
        np.testing.assert_array_equal(indices, expected["indices"])
        values = np.array(expected["values_real"]) + 1j * np.array(expected["values_imag"])
        grid.map(indices, values, "MAPPED")
        grid.reserve([expected["reserve_index"]], "RESERVED")
        np.testing.assert_array_equal(grid.extract(indices), values)
        assert list(grid.shape) == expected["python_shape"]
        matlab = grid.to_matlab()
        assert list(matlab.shape) == expected["matlab_shape"]
        linear = np.ravel_multi_index((indices[:, 2], indices[:, 1], indices[:, 0]), matlab.shape, order="F")
        np.testing.assert_array_equal(linear + 1, expected["linear_indices_1based"])
        flat = matlab.ravel(order="F")
        np.testing.assert_array_equal(flat[linear], values)
        assert grid.total_re_count == expected["total_re_count"]
        assert grid.occupied_re_count == expected["occupied_re_count"]
        assert np.count_nonzero(matlab) == expected["nonzero_count"]
        weights = np.arange(1, flat.size + 1)
        assert flat.real.sum() == expected["sum_real"]
        assert flat.imag.sum() == expected["sum_imag"]
        assert (flat.real * weights).sum() == expected["weighted_real"]
        assert (flat.imag * weights).sum() == expected["weighted_imag"]
