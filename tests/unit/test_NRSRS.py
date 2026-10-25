"""SRS 的调度边界、梳齿、功率、坐标、端口正交性及失败原子性。"""

from dataclasses import FrozenInstanceError, replace

import numpy as np
import pytest

from cell import NRCell
from grid import NRGrid
from srs import NRSRS


def test_default_configuration_and_copy_contract():
    cell = NRCell(n_tx_antennas=4)
    srs = NRSRS(cell)
    assert srs.cell is cell
    assert srs.n_ports == 1  # 不自动把物理天线数当 SRS 端口数。
    assert srs.antenna_ports == (1000,)
    assert srs.bandwidth_rb == 4 and srs.sequence_length == 24
    assert srs.symbol_start == 13 and srs.max_cyclic_shifts == 8
    assert srs.absolute_slot == 0 and srs.is_candidate_slot and srs.is_active
    assert srs.SPEC_BASELINE == "TS 38.211 V15.2.0; TS 38.331 V15.2.1"
    coordinates = srs.indices()
    np.testing.assert_array_equal(coordinates[:, 2], np.arange(0, 48, 2))
    np.testing.assert_array_equal(coordinates[:, 1], 13)
    assert coordinates.dtype == np.int64
    seq = srs.generate()
    np.testing.assert_allclose(np.abs(seq), 1, atol=1e-15)
    seq[:] = 0
    coordinates[:] = -1
    assert np.all(np.abs(srs.generate()) > 0.99)
    assert np.all(srs.indices() >= 0)
    with pytest.raises(FrozenInstanceError):
        srs.n_ports = 2
    config = srs.to_dict()
    assert len(config) == 19 and config["cell"] == cell.to_dict()
    config["cell"]["n_cell_id"] = 999
    assert srs.cell.n_cell_id == 1


INTEGER_FIELDS = ["n_ports", "n_symbols", "start_position", "c_srs", "b_srs", "b_hop", "k_tc",
                  "frequency_shift", "frequency_position", "sequence_id", "repetition", "periodicity",
                  "slot_offset", "comb_offset", "cyclic_shift"]


@pytest.mark.parametrize("name", INTEGER_FIELDS)
@pytest.mark.parametrize("value", [True, 1.0, np.int64(1)])
def test_strict_integer_types(name, value):
    with pytest.raises(TypeError, match=name):
        NRSRS(NRCell(), **{name: value})


@pytest.mark.parametrize("name,value", [("n_ports", 0), ("n_ports", 3), ("n_ports", 8),
    ("n_symbols", 3), ("n_symbols", 8), ("start_position", -1), ("start_position", 6),
    ("c_srs", 64), ("b_srs", 4), ("b_hop", -1), ("k_tc", 3), ("k_tc", 8),
    ("comb_offset", 2), ("cyclic_shift", 8), ("frequency_shift", 269),
    ("frequency_position", 68), ("sequence_id", 1024), ("repetition", 3),
    ("periodicity", 3), ("periodicity", 2561), ("slot_offset", 1)])
def test_r15_ranges(name, value):
    with pytest.raises(ValueError):
        NRSRS(NRCell(), **{name: value})


@pytest.mark.parametrize("kwargs,error", [({"cell": None}, TypeError),
    ({"n_symbols": 4, "start_position": 2}, ValueError), ({"repetition": 2}, ValueError),
    ({"group_seq_hopping": False}, TypeError), ({"group_seq_hopping": "random"}, ValueError),
    ({"resource_type": None}, TypeError), ({"resource_type": "off"}, ValueError),
    ({"resource_type": "aperiodic", "periodicity": 2}, ValueError), ({"enabled": 1}, TypeError)])
def test_joint_constraints(kwargs, error):
    config = {"cell": NRCell(), **kwargs}
    with pytest.raises(error):
        NRSRS(**config)


@pytest.mark.parametrize("cp", ["normal", "extended"])
@pytest.mark.parametrize("n_symbols", [1, 2, 4])
def test_last_six_symbols_and_extended_cp(cp, n_symbols):
    cell = NRCell(subcarrier_spacing_khz=60, cyclic_prefix=cp)
    srs = NRSRS(cell, n_symbols=n_symbols, start_position=5)
    expected = np.arange(cell.symbols_per_slot - 6, cell.symbols_per_slot - 6 + n_symbols)
    np.testing.assert_array_equal(np.unique(srs.indices()[:, 1]), expected)


@pytest.mark.parametrize("ports", [1, 2, 4])
@pytest.mark.parametrize("comb,shift", [(2, 0), (2, 7), (4, 0), (4, 11)])
def test_cyclic_shift_port_orthogonality_comb_and_power(ports, comb, shift):
    cell = NRCell(n_size_grid=24)
    srs = NRSRS(cell, n_ports=ports, k_tc=comb, cyclic_shift=shift, comb_offset=comb-1,
                n_symbols=2, start_position=2, c_srs=6)
    sequence = srs.generate().reshape(2, srs.sequence_length, ports)
    for symbol in sequence:
        np.testing.assert_allclose(symbol.conj().T @ symbol,
                                   np.eye(ports)*srs.sequence_length, atol=2e-10)
    coordinates = srs.indices().reshape(ports, 2, srs.sequence_length, 3)
    assert np.all(np.diff(coordinates[:, :, :, 2], axis=2) == comb)
    expected = np.full(ports, comb-1)
    if ports == 4 and shift >= srs.max_cyclic_shifts//2:
        expected[1::2] = (comb-1+comb//2) % comb
    np.testing.assert_array_equal(coordinates[:, 0, 0, 2], expected)
    grid = NRGrid(cell, ports+1)  # 允许额外未使用的逻辑端口。
    count = srs.map_to_grid(grid, beta=0.7, owner="SRS:UE0")
    assert count == ports*2*srs.sequence_length
    assert grid.occupied_re_count == count
    np.testing.assert_allclose(np.sum(np.abs(grid.data)**2), 0.7**2*2*srs.sequence_length, atol=1e-10)
    assert not np.any(grid.occupancy[-1])
    # 提取顺序须对应 generate 的 Fortran 扁平化顺序。
    np.testing.assert_allclose(grid.extract(srs.indices()), srs.generate().ravel(order="F")*0.7/np.sqrt(ports), atol=1e-14)


def test_frequency_hopping_hand_calculated_even_permutation_and_repetition():
    # 原表 C=3: m0=16,N0=1,m1=4,N1=4。F1(n) mod4 = 0,2,1,3。
    cell = NRCell(n_size_grid=16)
    srs = NRSRS(cell, c_srs=3, b_srs=1, b_hop=0, n_symbols=4, start_position=3)
    np.testing.assert_array_equal(srs._frequency_indices()[1], [[0, 96, 48, 144]])
    np.testing.assert_array_equal(replace(srs, repetition=2)._frequency_indices()[1], [[0, 0, 96, 96]])
    np.testing.assert_array_equal(replace(srs, repetition=4)._frequency_indices()[1], [[0, 0, 0, 0]])
    periodic_next = replace(srs, cell=cell.with_slot_offset(1), repetition=2)
    np.testing.assert_array_equal(periodic_next._frequency_indices()[1], [[48, 48, 144, 144]])
    # 非周期只在资源内部计数，在另一帧重新触发仍得到同样的频率图案。
    aperiodic = replace(periodic_next, resource_type="aperiodic")
    np.testing.assert_array_equal(aperiodic._frequency_indices()[1], [[0, 0, 96, 96]])


def test_bwp_and_crb_coordinates_do_not_silently_clip():
    cell = NRCell(n_size_grid=24, n_start_grid=10, bwp_start=14, bwp_size=8)
    good = NRSRS(cell, frequency_shift=4)
    assert good.indices()[0, 2] == 48
    assert good.indices()[-1, 2] == 94
    assert cell.n_start_grid + good.indices()[0, 2]//12 == 14
    for shift in (0, 9):
        bad = replace(good, frequency_shift=shift)
        grid = NRGrid(cell)
        with pytest.raises(ValueError, match="BWP"):
            bad.map_to_grid(grid)
        assert grid.occupied_re_count == 0 and not np.any(grid.data)
    # 窄带首跳可容纳，后续符号跳出 BWP 时整体拒绝。
    bad = NRSRS(NRCell(n_size_grid=4), c_srs=3, b_srs=1, n_symbols=4, start_position=3)
    with pytest.raises(ValueError, match="BWP"):
        bad.indices()


@pytest.mark.parametrize("resource", ["periodic", "semi-persistent", "aperiodic"])
def test_enabled_empty_and_matlab_adapter(resource):
    srs = NRSRS(NRCell(), resource_type=resource, enabled=False)
    assert not srs.is_active
    assert srs.indices().shape == (0, 3)
    assert srs.generate().shape == (0, 1)
    grid = NRGrid(srs.cell)
    assert srs.map_to_grid(grid) == 0 and grid.occupied_re_count == 0
    config = srs.to_matlab_config()
    assert config["SRSPeriod"] == "off"
    config = replace(srs, enabled=True).to_matlab_config()
    assert config["SRSPeriod"] == ("on" if resource == "aperiodic" else [1, 0])
    assert config["NumSRSPorts"] == 1 and config["SymbolStart"] == 13
    assert not config["SRSPositioning"] and not config["CyclicShiftHopping"]


def test_periodic_candidate_uses_frame_and_resets_at_sfn_wrap():
    cell = NRCell(n_frame=1, n_slot=0)
    srs = NRSRS(cell, periodicity=32, slot_offset=20)
    assert srs.absolute_slot == 20 and srs.is_active
    assert not replace(srs, cell=cell.with_slot_offset(1)).is_active
    assert replace(srs, cell=cell.with_slot_offset(1)).generate().size == 0
    edge = NRSRS(NRCell(n_frame=1023, n_slot=19), periodicity=2, slot_offset=1)
    assert edge.is_active
    assert not replace(edge, cell=edge.cell.with_slot_offset(1)).is_candidate_slot
    assert replace(srs, resource_type="aperiodic", periodicity=1, slot_offset=0).is_candidate_slot


def test_hopping_seed_independent_from_pci_and_frame_reinitialization():
    srs = NRSRS(NRCell(n_frame=5, n_slot=3), c_srs=6, sequence_id=1023,
                group_seq_hopping="groupHopping", n_symbols=4, start_position=3)
    other = replace(srs, cell=replace(srs.cell, n_frame=6, n_cell_id=999))
    np.testing.assert_array_equal(srs.generate(), other.generate())
    assert len(np.unique(srs.sequence_parameters()["u"])) > 1
    seq = replace(srs, group_seq_hopping="sequenceHopping")
    assert np.any(seq.sequence_parameters()["v"] == 1)
    short = replace(seq, c_srs=0)
    np.testing.assert_array_equal(short.sequence_parameters()["v"], 0)


@pytest.mark.parametrize("grid,beta,error", [(None, 1, TypeError),
    (NRGrid(NRCell(n_cell_id=2)), 1, ValueError), (NRGrid(NRCell()), True, TypeError),
    (NRGrid(NRCell()), 1j, TypeError), (NRGrid(NRCell()), -1, ValueError),
    (NRGrid(NRCell()), float("inf"), ValueError), (NRGrid(NRCell()), float("nan"), ValueError)])
def test_invalid_mapping(grid, beta, error):
    with pytest.raises(error):
        NRSRS(NRCell()).map_to_grid(grid, beta=beta)


def test_conflicts_port_validation_zero_gain_and_explicit_overwrite():
    srs = NRSRS(NRCell(), n_ports=2)
    with pytest.raises(ValueError, match="ports"):
        srs.map_to_grid(NRGrid(srs.cell))
    grid = NRGrid(srs.cell, 2)
    grid.reserve(srs.indices()[:1], "RESERVED")
    before = grid.data
    with pytest.raises(ValueError, match="collision"):
        srs.map_to_grid(grid)
    np.testing.assert_array_equal(grid.data, before)
    assert grid.occupied_re_count == 1
    count = srs.map_to_grid(grid, beta=0, overwrite=True)
    assert grid.occupied_re_count == count and not np.any(grid.data)
    with pytest.raises(ValueError, match="owner|blank"):
        srs.map_to_grid(grid, owner=" ", overwrite=True)
