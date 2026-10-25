"""公共 Gold 片段、SRS u/v 边界和无状态可重现性。"""

import numpy as np
import pytest

from common import NRCommon


def test_gold_segments_zero_length_and_independent_outputs():
    full = NRCommon.gold_sequence(42, 192)
    assert full.shape == (192,) and full.dtype == np.uint8
    assert set(full.tolist()) == {0, 1}
    np.testing.assert_array_equal(NRCommon.gold_sequence(42, 64, 128), full[128:])
    assert NRCommon.gold_sequence(42, 0, 500).shape == (0,)
    full[:] = 7
    assert np.all(NRCommon.gold_sequence(42, 192) <= 1)
    assert not np.array_equal(NRCommon.gold_sequence(0, 128), NRCommon.gold_sequence(1, 128))
    assert NRCommon.GOLD_NC == 1600 and NRCommon.GOLD_SEED_BITS == 31


@pytest.mark.parametrize("args,error", [((True, 1), TypeError), ((np.int64(1), 1), TypeError),
    ((-1, 1), ValueError), ((2**31, 1), ValueError), ((0, 1.0), TypeError),
    ((0, -1), ValueError), ((0, 1, True), TypeError), ((0, 1, -1), ValueError)])
def test_gold_validation(args, error):
    with pytest.raises(error):
        NRCommon.gold_sequence(*args)


def test_srs_uv_neither_and_sequence_threshold():
    args = dict(sequence_id=1023, n_slot=3, symbol_start=8, n_symbols=4, sequence_length=72)
    neither = NRCommon.srs_sequence_uv(**args)
    np.testing.assert_array_equal(neither["u"], [3]*4)
    np.testing.assert_array_equal(neither["v"], [0]*4)
    seq = NRCommon.srs_sequence_uv(**args, group_seq_hopping="sequenceHopping")
    np.testing.assert_array_equal(seq["v"], NRCommon.gold_sequence(1023, 4, 3*14+8))
    assert 1 in seq["v"]
    args["sequence_length"] = 60
    np.testing.assert_array_equal(NRCommon.srs_sequence_uv(**args, group_seq_hopping="sequenceHopping")["v"], 0)
    neither["u"][:] = -1
    np.testing.assert_array_equal(NRCommon.srs_sequence_uv(**args)["u"], 3)


def test_group_hopping_little_endian_and_extended_cp():
    # groupHopping 的8位权重必须是低位在前；不是把bit当作MSB字符串。
    for symbols_per_slot, start in [(14, 8), (12, 6)]:
        result = NRCommon.srs_sequence_uv(42, 1, start, 4, 36, "groupHopping", symbols_per_slot)
        bits = NRCommon.gold_sequence(42, 32, 8*(symbols_per_slot+start))
        expected = [(42+sum(int(bits[8*l+m]) << m for m in range(8))) % 30 for l in range(4)]
        np.testing.assert_array_equal(result["u"], expected)
        np.testing.assert_array_equal(result["v"], 0)
        assert result["u"].dtype == result["v"].dtype == np.int64


@pytest.mark.parametrize("kwargs,error", [({"sequence_id": True}, TypeError),
    ({"sequence_id": 1024}, ValueError), ({"n_slot": 160}, ValueError),
    ({"n_symbols": 3}, ValueError), ({"symbols_per_slot": 13}, ValueError),
    ({"symbol_start": 7}, ValueError), ({"symbol_start": 12}, ValueError),
    ({"sequence_length": 13}, ValueError), ({"sequence_length": 0}, ValueError),
    ({"group_seq_hopping": None}, TypeError), ({"group_seq_hopping": "both"}, ValueError)])
def test_uv_validation(kwargs, error):
    config = dict(sequence_id=42, n_slot=0, symbol_start=8, n_symbols=4, sequence_length=72)
    with pytest.raises(error):
        NRCommon.srs_sequence_uv(**(config | kwargs))
