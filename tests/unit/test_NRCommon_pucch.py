"""公用PUCCH规则：独立位权手算、不同Gold种子、CP坐标与短序列。"""

import numpy as np
import pytest

from common import NRCommon


def test_short_sequences_energy_orthogonality_and_copy():
    for group in range(30):
        sequences = np.array(
            [NRCommon.low_papr_sequence_12(group, cs) for cs in range(12)]
        )
        np.testing.assert_allclose(
            sequences @ sequences.conj().T, 12 * np.eye(12), atol=3e-13
        )
    a = NRCommon.low_papr_sequence_12(0)
    a[:] = 0
    assert np.linalg.norm(NRCommon.low_papr_sequence_12(0)) > 0
    for args in ((30, 0), (0, 12)):
        with pytest.raises(ValueError):
            NRCommon.low_papr_sequence_12(*args)


@pytest.mark.parametrize("mode", ["neither", "enable", "disable"])
def test_pucch_gold_seeds_and_extended_cp_uses_14(mode):
    nid = 1023
    slot = 39
    start = 10
    p = NRCommon.pucch_sequence_parameters(nid, slot, start, 2, 5, 3, mode, True, 12)
    expected = []
    for symbol in (10, 11):
        bits = NRCommon.gold_sequence(nid, 8, offset=8 * (14 * slot + symbol))
        expected.append(sum(int(bit) * 2**i for i, bit in enumerate(bits)))
    np.testing.assert_array_equal(p["n_cs"], expected)
    np.testing.assert_array_equal(p["cyclic_shift"], (np.array(expected) + 8) % 12)
    np.testing.assert_allclose(p["alpha"], 2 * np.pi * p["cyclic_shift"] / 12)
    for hop in (0, 1):
        if mode == "enable":
            b = NRCommon.gold_sequence(nid // 30, 8, offset=8 * (2 * slot + hop))
            assert (
                p["u"][hop] == (sum(int(x) * 2**i for i, x in enumerate(b)) + nid) % 30
            )
        elif mode == "disable":
            assert (
                p["v"][hop]
                == NRCommon.gold_sequence(
                    32 * (nid // 30) + nid % 30, 1, offset=2 * slot + hop
                )[0]
            )
        else:
            assert p["u"][hop] == nid % 30 and p["v"][hop] == 0


@pytest.mark.parametrize(
    "changes,error",
    [
        ({"hopping_id": 1024}, ValueError),
        ({"n_slot": 160}, ValueError),
        ({"n_symbols": 3}, ValueError),
        ({"symbols_per_slot": 13}, ValueError),
        ({"symbols_per_slot": 12, "n_slot": 40}, ValueError),
        ({"symbol_start": 14}, ValueError),
        ({"frequency_hopping": 1}, TypeError),
        ({"frequency_hopping": True}, ValueError),
        ({"group_hopping": "bad"}, ValueError),
        ({"m_cs": 12}, ValueError),
    ],
)
def test_pucch_parameter_validation(changes, error):
    with pytest.raises(error):
        NRCommon.pucch_sequence_parameters(
            **(
                {"hopping_id": 1, "n_slot": 0, "symbol_start": 0, "n_symbols": 1}
                | changes
            )
        )
