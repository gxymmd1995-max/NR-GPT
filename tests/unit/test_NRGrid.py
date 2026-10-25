"""资源网格的维度、坐标、原子映射、零值占用、冲突和外部副本隔离。"""

import numpy as np
import pytest

from cell import NRCell
from grid import NRGrid


def test_empty_grid_and_metadata():
    cell = NRCell(n_tx_antennas=4)
    grid = NRGrid(cell)
    assert grid.cell is cell
    assert grid.n_ports == 1
    assert grid.n_symbols == 14
    assert grid.n_subcarriers == 624
    assert grid.shape == (1, 14, 624)
    assert grid.data.dtype == np.complex128
    assert not np.any(grid.data)
    assert not np.any(grid.occupancy)
    assert grid.owners.shape == grid.shape
    assert grid.total_re_count == grid.free_re_count == 8736
    assert grid.occupied_re_count == 0
    assert grid.summary() == {
        "cell": cell.to_dict(), "n_ports": 1, "domain": "port",
        "axis_order": ("port", "symbol", "subcarrier"), "shape": (1, 14, 624),
        "dtype": "complex128", "total_re_count": 8736, "occupied_re_count": 0, "free_re_count": 8736,
    }


def test_extended_cp_and_read_only_configuration():
    grid = NRGrid(NRCell(subcarrier_spacing_khz=60, cyclic_prefix="extended"), n_ports=2)
    assert grid.shape == (2, 12, 624)
    with pytest.raises(AttributeError):
        grid.cell = NRCell()
    with pytest.raises(AttributeError):
        grid.n_ports = 3


@pytest.mark.parametrize("cell,ports,error", [(None, 1, TypeError), (NRCell(), True, TypeError),
                                            (NRCell(), 1.0, TypeError), (NRCell(), 0, ValueError),
                                            (NRCell(), -1, ValueError)])
def test_invalid_constructor(cell, ports, error):
    with pytest.raises(error):
        NRGrid(cell, ports)


def test_bwp_coordinate_origins_and_order():
    grid = NRGrid(NRCell(n_start_grid=10, bwp_start=20, bwp_size=24), 2)
    indices = grid.bwp_indices([1, 0], [3, 1], [1, 0])
    assert indices.shape == (96, 3)
    assert indices.dtype == np.int64
    np.testing.assert_array_equal(indices[:2], [[1, 3, 132], [1, 3, 133]])
    np.testing.assert_array_equal(indices[12], [1, 3, 120])
    np.testing.assert_array_equal(indices[24], [1, 1, 132])
    np.testing.assert_array_equal(indices[48], [0, 3, 132])
    np.testing.assert_array_equal(indices[-1], [0, 1, 131])
    assert grid.bwp_indices([0], [0]).shape == (24, 3)


@pytest.mark.parametrize("prbs,symbols,ports,error", [
    ([[0]], [0], None, ValueError), ([0.0], [0], None, TypeError),
    ([True, 0], [0], None, TypeError), ([-1], [0], None, ValueError),
    ([52], [0], None, ValueError), ([0, 0], [0], None, ValueError),
    ([0], [14], None, ValueError), ([0], [0], [1], ValueError),
    ([0], [0], [True], TypeError),
])
def test_bad_bwp_selection(prbs, symbols, ports, error):
    with pytest.raises(error):
        NRGrid(NRCell()).bwp_indices(prbs, symbols, ports)


@pytest.mark.parametrize("prbs,symbols,ports", [([], [0], None), ([0], [], None), ([0], [0], [])])
def test_empty_bwp_selection(prbs, symbols, ports):
    assert NRGrid(NRCell()).bwp_indices(prbs, symbols, ports).shape == (0, 3)


def test_scalar_and_vector_mapping_and_copy_isolation():
    grid = NRGrid(NRCell(n_size_grid=2), 2)
    indices = [[0, 0, 0], [1, 13, 23]]
    assert grid.map(indices, [1 + 2j, 3 - 4j], "DATA") == 2
    np.testing.assert_array_equal(grid.extract(indices[::-1]), [3 - 4j, 1 + 2j])
    np.testing.assert_array_equal(grid.extract([indices[0], indices[0]]), [1 + 2j, 1 + 2j])
    assert grid.map([[0, 1, 1], [0, 1, 2]], 2j, "SCALAR") == 2
    for value in (grid.data, grid.owners, grid.occupancy, grid.extract(indices)):
        value[...] = 0
    np.testing.assert_array_equal(grid.extract(indices), [1 + 2j, 3 - 4j])
    assert grid.owners[0, 0, 0] == "DATA"
    assert grid.occupied_re_count == 4


def test_zero_values_and_reservation_are_occupied():
    grid = NRGrid(NRCell())
    grid.map([[0, 0, 0]], 0, "ZERO")
    assert grid.reserve([[0, 1, 1]], "RESERVED") == 1
    assert grid.data[0, 0, 0] == grid.data[0, 1, 1] == 0
    assert grid.occupied_re_count == 2
    with pytest.raises(ValueError, match="collision"):
        grid.map([[0, 0, 0]], 1, "ZERO")
    with pytest.raises(ValueError, match="collision"):
        grid.reserve([[0, 1, 1]], "RESERVED")
    assert grid.map([[0, 1, 1]], 4, "FILLED", overwrite=True) == 1
    assert grid.owners[0, 1, 1] == "FILLED"
    assert grid.occupied_re_count == 2


@pytest.mark.parametrize("indices,error", [
    ([0, 0, 0], ValueError), ([[0, 0]], ValueError),
    ([[False, 0, 0]], TypeError), ([[0, 0, 0.0]], TypeError),
    ([[0, 0, -1]], ValueError), ([[0, 0, 624]], ValueError),
    ([[1, 0, 0]], ValueError), ([[0, 14, 0]], ValueError),
    (np.array([[0, 0, 2**64 - 1]], dtype=np.uint64), ValueError),
])
def test_invalid_indices(indices, error):
    with pytest.raises(error):
        NRGrid(NRCell()).extract(indices)


@pytest.mark.parametrize("owner,error", [(None, TypeError), ("", ValueError), ("  ", ValueError), ("X" * 65, ValueError)])
def test_invalid_owner(owner, error):
    with pytest.raises(error):
        NRGrid(NRCell()).map([[0, 0, 0]], 1, owner)


def test_failed_operations_do_not_partially_write():
    grid = NRGrid(NRCell())
    grid.map([[0, 0, 0]], 3j, "EXISTING")
    before = grid.data
    before_owner = grid.owners
    for coordinates, values, kwargs in [
        ([[0, 0, 0], [0, 0, 1]], [1, 2], {}),
        ([[0, 0, 1], [0, 0, 1]], [1, 2], {}),
        ([[0, 0, 1]], [1, 2], {}),
        ([[0, 0, 1]], [[1]], {}),
        ([[0, 0, 1]], np.nan, {}),
        ([[0, 0, 1]], np.inf, {}),
        ([], np.nan, {}),
        ([[0, 0, 1]], 2, {"overwrite": 1}),
    ]:
        with pytest.raises((ValueError, TypeError)):
            grid.map(coordinates, values, "NEW", **kwargs)
        np.testing.assert_array_equal(grid.data, before)
        np.testing.assert_array_equal(grid.owners, before_owner)


def test_empty_map_extract_and_clear():
    grid = NRGrid(NRCell())
    assert grid.map([], [], "EMPTY") == 0
    assert grid.reserve([], "EMPTY") == 0
    assert grid.extract([]).shape == (0,)
    grid.map([[0, 0, 0]], 1, "A")
    grid.reserve([[0, 0, 1]], "B")
    assert grid.clear("A") == 1
    assert grid.extract([[0, 0, 0]])[0] == 0
    assert grid.clear("MISSING") == 0
    assert grid.clear() == 1
    assert grid.free_re_count == grid.total_re_count
    assert grid.clear() == 0


def test_matlab_axis_order_and_linear_positions():
    grid = NRGrid(NRCell(n_size_grid=1), 2)
    grid.map([[0, 0, 1], [1, 13, 11]], [2j, 3 - 4j], "A")
    matlab = grid.to_matlab()
    assert matlab.shape == (12, 14, 2)
    assert matlab[1, 0, 0] == 2j
    assert matlab[11, 13, 1] == 3 - 4j
    assert matlab.ravel(order="F")[1] == 2j
    assert matlab.ravel(order="F")[-1] == 3 - 4j
    matlab[...] = 0
    assert grid.extract([[0, 0, 1]])[0] == 2j
    assert NRGrid(NRCell(n_size_grid=1)).to_matlab().shape == (12, 14, 1)
