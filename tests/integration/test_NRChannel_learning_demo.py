"""Exercise every learning group and check the intended resource contrast."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest


@pytest.fixture(scope="module")
def demo():
    path = (
        Path(__file__).resolve().parents[2]
        / "examples/common/NRChannel_learning_demo.py"
    )
    spec = importlib.util.spec_from_file_location("nr_learning_demo", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "group,label,expected_re",
    [
        ("pdcch", 1, [216, 216, 216]),
        ("pdsch", 1, [168, 312, 624]),
        ("pusch", 1, [168, 312, 624]),
        ("ssb", 2, [144, 144]),
        ("srs", 2, [24, 48, 96]),
        ("csirs", 2, [72, 24, 12]),
        ("ul-ptrs", 2, [52, 24, 12]),
        ("dl-ptrs", 2, [52, 24, 12]),
    ],
)
def test_learning_cases(demo, group, label, expected_re):
    cases = [demo.run_case(group, setting) for setting in demo.SETTINGS[group]]
    assert [np.count_nonzero(case["grid"] == label) for case in cases] == expected_re
    for case in cases:
        cell = case["cell"]
        assert case["passed"], case["detail"]
        assert case["wave"].shape == (cell.samples_per_slot,)
        assert np.any(case["wave"])
    if group == "ssb":
        assert not np.array_equal(cases[0]["grid"] == 2, cases[1]["grid"] == 2)
    elif group in ("pdcch", "pdsch", "pusch", "srs"):
        active = [np.count_nonzero(np.any(case["grid"], axis=1)) for case in cases]
        assert active == list(demo.SETTINGS[group])


def test_pdsch_snr_comparison_changes_receiver_outcome(demo):
    high, low = (case for _, case in demo.pdsch_snr_cases())
    np.testing.assert_array_equal(high["grid"], low["grid"])
    np.testing.assert_array_equal(high["wave"], low["wave"])
    assert high["passed"]
    assert low["result"]["detected"]
    assert not low["result"]["crc_ok"]
