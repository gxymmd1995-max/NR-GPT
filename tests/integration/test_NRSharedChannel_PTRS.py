"""Check PT-RS reservation, modulation and phase compensation for UL and DL."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from cell import NRCell
from grid import NRGrid
from pdsch import NRPDSCH, NRPDSCHTransmitter
from pusch import NRPUSCH, NRPUSCHTransmitter


@pytest.fixture(scope="module")
def demo():
    path = (
        Path(__file__).resolve().parents[2]
        / "examples/common/NRSharedChannel_PTRS_demo.py"
    )
    spec = importlib.util.spec_from_file_location("shared_ptrs_demo", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("direction", ["ul", "dl"])
def test_same_waveform_before_and_after_phase_correction(demo, direction):
    case = demo.run_case(direction)
    assert case["before"]["detected"]
    assert case["before"]["ptrs_phase_rad"] is None
    assert not case["before"]["crc_ok"]
    assert case["passed"]
    np.testing.assert_allclose(
        case["after"]["ptrs_phase_rad"], case["phase"], atol=1e-12
    )


@pytest.mark.parametrize(
    ("resource_cls", "transmitter"),
    [
        (NRPDSCH, NRPDSCHTransmitter),
        (NRPUSCH, NRPUSCHTransmitter),
    ],
)
def test_reservation_and_invalid_config(resource_cls, transmitter):
    cell = NRCell(n_size_grid=16, n_start_grid=4, bwp_start=6, bwp_size=12)
    baseline = resource_cls(cell, n_prbs=8)
    resource = resource_cls(cell, n_prbs=8, ptrs_config=(2, 2, 1))
    pt = resource.ptrs.indices()
    indices = set(map(tuple, resource.indices()))
    assert indices.isdisjoint(map(tuple, pt))
    assert baseline.coded_length - resource.coded_length == 2 * len(pt)
    tx = transmitter(resource).transmit([0, 1] * 16)
    np.testing.assert_allclose(tx["grid"].data[tuple(pt.T)], resource.ptrs.generate())
    grid = NRGrid(cell, 1)
    grid.map(pt[:1], [1], owner="existing")
    with pytest.raises(ValueError, match="collision"):
        resource.map_to_grid(grid, tx["coded_bits"])
    assert np.count_nonzero(grid.occupancy) == 1

    for invalid in ([2, 2, 1], (2, 2)):
        with pytest.raises(TypeError, match="ptrs_config"):
            resource_cls(cell, ptrs_config=invalid)
    with pytest.raises(ValueError, match="one layer"):
        resource_cls(cell, n_layers=2, ptrs_config=(2, 2, 1))
    with pytest.raises(ValueError, match="one DM-RS"):
        resource_cls(cell, dmrs_length=2, ptrs_config=(2, 2, 1))


@pytest.mark.parametrize("resource_cls", [NRPDSCH, NRPUSCH])
def test_allocation_without_ptrs_symbols_preserves_data_budget(resource_cls):
    cell = NRCell()
    baseline = resource_cls(cell, start_symbol=2, n_symbols=4)
    resource = resource_cls(cell, start_symbol=2, n_symbols=4, ptrs_config=(4, 2, 0))
    assert not len(resource.ptrs.indices())
    assert resource.coded_length == baseline.coded_length
    np.testing.assert_array_equal(resource.indices(), baseline.indices())
