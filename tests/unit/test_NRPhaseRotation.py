"""R15逐符号载波相位与提前FFT窗口的正负号、单位和返回副本。"""

from dataclasses import replace

import numpy as np
import pytest

from cell import NRCell
from common import NRPhaseRotation


def test_symbol_phase_origin_inverse_and_subframe_reset():
    cell = NRCell(n_size_grid=1, subcarrier_spacing_khz=60, n_slot=1)
    phase = NRPhaseRotation(cell, 3500000123)
    timing = cell.symbol_timing(0)
    expected = (
        -2
        * np.pi
        * 3500000123
        * (timing["start_sample_in_subframe"] + timing["cp_samples"])
        / cell.sample_rate_hz
    )
    np.testing.assert_allclose(phase.symbol_phases()[0], expected, atol=1e-8)
    np.testing.assert_allclose(
        phase.symbol_phasors() * phase.symbol_phasors(True), 1, atol=1e-15
    )
    np.testing.assert_array_equal(
        phase.symbol_phasors(),
        NRPhaseRotation(
            replace(cell, n_slot=5, n_frame=7), 3500000123
        ).symbol_phasors(),
    )
    grid = np.ones((2, 14, 12), complex)
    np.testing.assert_allclose(
        phase.apply_grid(phase.apply_grid(grid), True), grid, atol=1e-15
    )
    phases = phase.symbol_phases()
    phases[:] = 0
    assert np.any(phase.symbol_phases() != 0)


def test_timing_and_fft_window_signs():
    phase = NRPhaseRotation(NRCell(n_size_grid=1))
    bins = np.arange(12) - 6
    np.testing.assert_allclose(
        phase.timing_phasors(1.25), np.exp(-2j * np.pi * bins * 1.25 / 128), atol=1e-15
    )
    np.testing.assert_allclose(
        phase.timing_phasors(3) * phase.fft_window_phasors(3), 1, atol=1e-15
    )


@pytest.mark.parametrize(
    "grid",
    [
        np.ones((14, 12)),
        np.ones((0, 14, 12)),
        np.ones((1, 12, 14)),
        np.full((1, 14, 12), np.inf),
    ],
)
def test_grid_validation(grid):
    with pytest.raises(ValueError):
        NRPhaseRotation(NRCell(n_size_grid=1)).apply_grid(grid)


def test_phase_argument_validation():
    phase = NRPhaseRotation(NRCell())
    with pytest.raises(TypeError):
        phase.symbol_phasors(1)
    with pytest.raises(TypeError):
        phase.timing_phasors(True)
    with pytest.raises(ValueError):
        phase.fft_window_phasors(-1)
