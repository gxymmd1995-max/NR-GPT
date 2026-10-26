"""标准码本的坐标、归一化、输入边界与RI/TPMI选择约束。"""

import numpy as np
import pytest

from common import NRUplinkCodebook


def test_matrices_preserve_standard_power_and_return_copies():
    np.testing.assert_allclose(NRUplinkCodebook.matrix(2, 1, 0), [[1/np.sqrt(2)], [0]])
    np.testing.assert_allclose(NRUplinkCodebook.matrix(2, 1, 4), [[1/np.sqrt(2)], [1j/np.sqrt(2)]])
    np.testing.assert_allclose(NRUplinkCodebook.matrix(4, 4, 0), np.eye(4)/2)
    w = NRUplinkCodebook.matrix(4, 3, 0)
    assert w.shape == (4, 3) and np.isclose(np.linalg.norm(w)**2, .75)
    w[:] = 0
    assert np.any(NRUplinkCodebook.matrix(4, 3, 0))


@pytest.mark.parametrize("args,error", [((3, 1, 0), ValueError), ((True, 1, 0), TypeError),
    ((2, 3, 0), ValueError), ((2, 1, 6), ValueError), ((4, 2, -1), ValueError), ((1, 1, False), TypeError)])
def test_invalid_matrix(args, error):
    with pytest.raises(error):
        NRUplinkCodebook.matrix(*args)


def test_identity_selects_full_rank_and_single_path_selects_one():
    full = NRUplinkCodebook.select(np.eye(4)[None], .001)
    assert full["ri"] == 4 and full["tpmi"] == 0
    # rank-one H 的每根Tx天线完全相干；RI=1胜出，不依赖矩阵元素是否非零。
    rank_one = NRUplinkCodebook.select(np.ones((3, 4, 4)), .01)
    assert rank_one["ri"] == 1
    assert NRUplinkCodebook.select(np.zeros((1, 1, 1)), 0)["ri"] is None
    assert NRUplinkCodebook.select(np.ones((1, 1, 1)), 1, tx_power=0)["tpmi"] is None


def test_rank_limit_subset_and_white_noise_monotonicity():
    h = np.eye(4)[None].repeat(4, axis=0)
    limited = NRUplinkCodebook.select(h, .1, max_rank=2, allowed_tpmi={2: [3, 1]})
    assert limited["ri"] == 2 and limited["tpmi"] == 1
    assert NRUplinkCodebook.select(h, .01)["score_bps_hz"] > NRUplinkCodebook.select(h, 1)["score_bps_hz"]
    assert NRUplinkCodebook.select(np.ones((1, 2, 4)), .1)["ri"] <= 2


@pytest.mark.parametrize("h,noise,kwargs,error", [
    (np.ones((2, 2)), .1, {}, ValueError), (np.ones((1, 2, 3)), .1, {}, ValueError),
    (np.full((1, 2, 2), np.nan), .1, {}, ValueError), (np.empty((0, 2, 2)), .1, {}, ValueError),
    (np.ones((1, 2, 2)), True, {}, TypeError), (np.ones((1, 2, 2)), -1, {}, ValueError),
    (np.ones((1, 2, 2)), float("nan"), {}, ValueError),
    (np.ones((1, 2, 2)), .1, {"tx_power": 1j}, TypeError),
    (np.ones((1, 2, 2)), .1, {"max_rank": 3}, ValueError),
    (np.ones((1, 2, 2)), .1, {"allowed_tpmi": []}, ValueError),
    (np.ones((1, 2, 2)), .1, {"allowed_tpmi": {}}, ValueError),
    (np.ones((1, 2, 2)), .1, {"allowed_tpmi": {1: []}}, ValueError),
    (np.ones((1, 2, 2)), .1, {"allowed_tpmi": {1: [0, 0]}}, ValueError),
    (np.ones((1, 2, 2)), .1, {"allowed_tpmi": {1: [9]}}, ValueError),
    (np.ones((1, 2, 2)), .1, {"allowed_tpmi": {3: [0]}}, ValueError)])
def test_selector_validation(h, noise, kwargs, error):
    with pytest.raises(error):
        NRUplinkCodebook.select(h, noise, **kwargs)
