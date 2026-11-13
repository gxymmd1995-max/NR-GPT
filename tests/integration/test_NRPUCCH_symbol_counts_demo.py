"""Check the symbol-length sweep against the actual mapped and decoded PUCCH."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest


@pytest.fixture(scope="module")
def demo():
    path = (
        Path(__file__).resolve().parents[2]
        / "examples/pucch/NRPUCCH_symbol_counts_demo.py"
    )
    spec = importlib.util.spec_from_file_location("pucch_symbol_counts_demo", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("cp,slot_symbols", [("normal", 14), ("extended", 12)])
def test_symbol_count_sweep(demo, cp, slot_symbols):
    expected = [
        (fmt, length)
        for fmt in range(5)
        for length in ((1, 2) if fmt in (0, 2) else range(4, slot_symbols + 1))
    ]
    assert demo.select_cases(slot_symbols, all_lengths=True) == expected
    assert len(demo.select_cases(slot_symbols)) == 13
    assert demo.select_cases(slot_symbols, fmt=2, n_symbols=3) == []

    for fmt, length in expected:
        case = demo.run_case(fmt, length, cp)
        grid = case["occupancy"]
        start = slot_symbols - length
        np.testing.assert_array_equal(
            np.flatnonzero(np.any(grid, axis=1)), np.arange(start, slot_symbols)
        )
        assert len(case["waveform"]) == case["sample_edges"][-1]
        assert not np.any(case["waveform"][: case["sample_edges"][start]])
        assert np.any(case["waveform"][case["sample_edges"][start] :])
        assert case["passed"], (cp, fmt, length, case["decoded"])
        if fmt == 0:
            assert not np.any(grid == 2)
        elif fmt == 1:
            np.testing.assert_array_equal(
                np.flatnonzero(np.any(grid == 2, axis=1)),
                np.arange(start, slot_symbols, 2),
            )
        elif fmt == 2:
            np.testing.assert_array_equal(
                np.count_nonzero(grid[start:] == 2, axis=1), 8
            )
        else:
            assert np.count_nonzero(grid == 2) == (1 if length == 4 else 2) * (
                24 if fmt == 3 else 12
            )
