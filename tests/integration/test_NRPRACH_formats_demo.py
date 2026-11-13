"""PRACH example coverage, time-domain boundaries and delayed detection."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest


@pytest.fixture(scope="module")
def demo():
    path = (
        Path(__file__).resolve().parents[2] / "examples/prach/NRPRACH_formats_demo.py"
    )
    spec = importlib.util.spec_from_file_location("prach_formats_demo", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_default_and_full_selection(demo):
    default = demo.select_cases()
    assert len(default) == 16
    assert {fmt for fmt, _, _ in default} == {
        "0",
        "1",
        "2",
        "3",
        "A1",
        "A2",
        "A3",
        "B1",
        "B2",
        "B3",
        "B4",
        "C0",
        "C2",
    }
    assert demo.select_cases(group="long", ra_scs=5, ul_scs=60) == [("3", 5, 60)]
    assert demo.select_cases(preamble_format="A1", ra_scs=120, ul_scs=30) == []
    all_pairs = demo.select_cases(all_pairs=True)
    assert len(set(all_pairs)) == len(all_pairs) == 102
    assert {ul for fmt, ra, ul in all_pairs if fmt == "A1" and ra == 120} == {60, 120}


@pytest.mark.parametrize(
    "fmt,ra,ul,cp,periods",
    [
        ("0", 1.25, 30, 3168, 1),
        ("1", 1.25, 30, 21024, 2),
        ("2", 1.25, 30, 4688, 4),
        ("3", 5, 30, 3168, 4),
        ("A1", 15, 30, 304, 2),
        ("A1", 30, 30, 160, 2),
        ("A1", 60, 60, 176, 2),
        ("A1", 120, 120, 208, 2),
        ("C2", 15, 30, 2064, 4),
    ],
)
def test_waveform_and_detection(demo, fmt, ra, ul, cp, periods):
    case = demo.run_case(fmt, ra, ul)
    resource = case["resource"]
    wave = case["waveform"]
    fft_ra = int(1024 * ul / ra)
    assert resource.cp_samples == cp
    assert len(wave) == cp + periods * fft_ra + 32
    useful = wave[cp : cp + fft_ra]
    assert np.any(useful)
    np.testing.assert_array_equal(wave[:cp], useful[np.arange(-cp, 0) % fft_ra])
    np.testing.assert_array_equal(wave[cp:-32], np.tile(useful, periods))
    np.testing.assert_array_equal(wave[-32:], 0)
    assert case["passed"]
