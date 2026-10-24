"""NRCell 独立期望值、边界、非法输入与状态转换测试。"""

from dataclasses import FrozenInstanceError, replace

import pytest

from cell import NRCell


@pytest.mark.parametrize("scs,mu,slots", [(15, 0, 1), (30, 1, 2), (60, 2, 4), (120, 3, 8), (240, 4, 16)])
def test_r15_numerology_table(scs, mu, slots):
    """期望值来自 TS 38.211 表 4.2-1、4.3.2-1，非复制被测公式。"""
    cell = NRCell(subcarrier_spacing_khz=scs)
    assert (cell.numerology, cell.slots_per_subframe, cell.slots_per_frame) == (mu, slots, slots * 10)
    assert cell.symbols_per_slot == 14
    assert cell.nominal_slot_duration_s == pytest.approx(0.001 / slots)


def test_defaults_and_bandwidth():
    cell = NRCell()
    assert cell.to_dict() == dict(n_cell_id=1, subcarrier_spacing_khz=30, cyclic_prefix="normal", n_size_grid=52,
                                 n_start_grid=0, bwp_start=0, bwp_size=52, n_frame=0, n_slot=0,
                                 duplex_mode="TDD", n_tx_antennas=1, n_rx_antennas=1)
    assert cell.n_subcarriers == 624
    assert cell.bwp_n_subcarriers == 624
    assert cell.occupied_bandwidth_hz == 18_720_000
    assert (cell.SUBCARRIERS_PER_RB, cell.SUBFRAMES_PER_FRAME, cell.FRAME_DURATION_S, cell.SFN_MODULUS) == (12, 10, 0.01, 1024)


def test_extended_cp():
    cell = NRCell(subcarrier_spacing_khz=60, cyclic_prefix="extended")
    assert (cell.symbols_per_slot, cell.slots_per_subframe, cell.slots_per_frame) == (12, 4, 40)


@pytest.mark.parametrize("kwargs", [
    {"n_cell_id": -1}, {"n_cell_id": 1008}, {"subcarrier_spacing_khz": 45},
    {"subcarrier_spacing_khz": 480}, {"cyclic_prefix": "NORMAL"},
    {"cyclic_prefix": "extended"}, {"n_size_grid": 0}, {"n_size_grid": 276},
    {"n_start_grid": -1}, {"n_start_grid": 2200}, {"bwp_start": -1},
    {"bwp_start": 1}, {"bwp_size": 53}, {"bwp_size": 0},
    {"n_start_grid": 10, "bwp_start": 9, "bwp_size": 1},
    {"n_frame": -1}, {"n_frame": 1024}, {"n_slot": -1}, {"n_slot": 20},
])
def test_reject_invalid_values(kwargs):
    with pytest.raises(ValueError):
        NRCell(**kwargs)


@pytest.mark.parametrize("field", ["n_cell_id", "subcarrier_spacing_khz", "n_size_grid", "n_start_grid", "bwp_start", "bwp_size", "n_frame", "n_slot"])
@pytest.mark.parametrize("value", [True, 1.0, "1"])
def test_reject_non_integer_fields(field, value):
    with pytest.raises(TypeError, match=field):
        NRCell(**{field: value})


def test_reject_non_string_cp():
    with pytest.raises(TypeError, match="cyclic_prefix"):
        NRCell(cyclic_prefix=None)


@pytest.mark.parametrize("pci,group,within", [(0, 0, 0), (42, 14, 0), (1007, 335, 2)])
def test_pci_components(pci, group, within):
    cell = NRCell(n_cell_id=pci)
    assert (cell.n_id_1, cell.n_id_2) == (group, within)


def test_nonzero_carrier_and_bwp_coordinates():
    cell = NRCell(n_start_grid=10, bwp_start=20, bwp_size=24)
    assert cell.bwp_n_subcarriers == 288
    assert cell.prb_to_crb(0) == 20
    assert cell.prb_to_crb(23) == 43
    assert cell.crb_to_prb(20) == 0
    assert cell.crb_to_prb(43) == 23
    assert cell.subcarrier_offset_hz(0) == 3_600_000
    assert cell.subcarrier_offset_hz(623) == 22_290_000


@pytest.mark.parametrize("method,index", [("prb_to_crb", -1), ("prb_to_crb", 24), ("crb_to_prb", 19),
                                         ("crb_to_prb", 44), ("subcarrier_offset_hz", -1), ("subcarrier_offset_hz", 624)])
def test_coordinate_bounds(method, index):
    cell = NRCell(n_start_grid=10, bwp_start=20, bwp_size=24)
    with pytest.raises(ValueError):
        getattr(cell, method)(index)


@pytest.mark.parametrize("method", ["prb_to_crb", "crb_to_prb", "subcarrier_offset_hz", "with_slot_offset"])
@pytest.mark.parametrize("index", [True, 1.5])
def test_method_index_types(method, index):
    with pytest.raises(TypeError):
        getattr(NRCell(), method)(index)


def test_time_indices_and_wrap():
    cell = NRCell(n_frame=1023, n_slot=19)
    assert (cell.subframe_index, cell.slot_in_subframe) == (9, 1)
    next_cell = cell.with_slot_offset()
    assert (next_cell.n_frame, next_cell.n_slot) == (0, 0)
    assert next_cell.with_slot_offset(-1) == cell
    assert cell.n_frame == 1023  # 原配置未被修改。
    assert NRCell().with_slot_offset(20 * 1024) == NRCell()
    assert NRCell().with_slot_offset(-21) == NRCell(n_frame=1022, n_slot=19)


def test_boundary_grid_and_bwp():
    cell = NRCell(n_start_grid=2199, n_size_grid=275, bwp_start=2473, bwp_size=1)
    assert cell.prb_to_crb(0) == 2473
    assert NRCell(n_size_grid=1).bwp_size == 1


def test_immutable_and_serialization():
    cell = NRCell(bwp_size=24)
    with pytest.raises(FrozenInstanceError):
        cell.n_cell_id = 2
    assert NRCell(**cell.to_dict()) == cell
    assert replace(cell, n_cell_id=42).n_cell_id == 42
    assert cell.to_matlab_config() == {"NCellID": 1, "SubcarrierSpacing": 30, "CyclicPrefix": "normal",
                                       "NSizeGrid": 52, "NStartGrid": 0, "NFrame": 0, "NSlot": 0}


@pytest.mark.parametrize("mode", ["TDD", "FDD"])
def test_duplex_and_antennas(mode):
    cell = NRCell(duplex_mode=mode, n_tx_antennas=4, n_rx_antennas=2)
    assert (cell.duplex_mode, cell.n_tx_antennas, cell.n_rx_antennas) == (mode, 4, 2)
    assert NRCell(**cell.to_dict()) == cell
    assert cell.n_fft == NRCell().n_fft  # 天线分支不乘入 FFT 尺寸。


@pytest.mark.parametrize("value", ["tdd", "FLEX", ""])
def test_invalid_duplex(value):
    with pytest.raises(ValueError, match="duplex_mode"):
        NRCell(duplex_mode=value)


@pytest.mark.parametrize("value", [True, None, 1])
def test_duplex_type(value):
    with pytest.raises(TypeError, match="duplex_mode"):
        NRCell(duplex_mode=value)


@pytest.mark.parametrize("field", ["n_tx_antennas", "n_rx_antennas"])
@pytest.mark.parametrize("value", [0, -1, True, 1.0, "2"])
def test_invalid_antennas(field, value):
    with pytest.raises(TypeError if type(value) is not int else ValueError, match=field):
        NRCell(**{field: value})


@pytest.mark.parametrize("nrb,nfft", [(1, 128), (10, 128), (11, 256), (21, 256), (22, 512),
                                     (42, 512), (43, 1024), (85, 1024), (86, 2048),
                                     (170, 2048), (171, 4096), (275, 4096)])
def test_fft_transition_boundaries(nrb, nfft):
    assert NRCell(n_size_grid=nrb).n_fft == nfft


def test_default_timing_values():
    cell = NRCell()
    assert cell.subframes_per_frame == 10
    assert cell.symbols_per_subframe == 28
    assert cell.symbols_per_frame == 280
    assert cell.resource_elements_per_slot == 8736
    assert cell.n_fft == 1024
    assert cell.sample_rate_hz == 30_720_000
    assert cell.TC_FREQUENCY_HZ == 1_966_080_000
    assert cell.TS_FREQUENCY_HZ == 30_720_000
    assert cell.KAPPA == 64
    assert cell.MIN_FFT_SIZE == 128
    assert cell.tc_s == pytest.approx(1 / 1_966_080_000)
    assert cell.ts_s == pytest.approx(1 / 30_720_000)
    assert cell.ts_s / cell.tc_s == pytest.approx(64)
    assert cell.sample_period_s == pytest.approx(cell.ts_s)
    assert cell.tc_per_sample == 64
    assert cell.useful_symbol_length_tc == 65536
    assert cell.cp_lengths_tc[:2] == (5632, 4608)
    assert cell.symbol_lengths_tc[:2] == (71168, 70144)
    assert cell.cp_lengths_samples[:2] == (88, 72)
    assert cell.symbol_lengths_samples[:2] == (1112, 1096)
    assert cell.symbol_start_samples[:3] == (0, 1112, 2208)
    assert cell.samples_per_slot == 15360
    assert cell.samples_per_subframe == 30720
    assert cell.samples_per_frame == 307200
    assert cell.slot_start_sample == 0
    assert cell.slot_duration_s == pytest.approx(0.0005)
    assert cell.symbol_timing(0) == {
        "symbol": 0, "symbol_in_subframe": 0, "cp_length_tc": 5632,
        "useful_length_tc": 65536, "total_length_tc": 71168,
        "cp_samples": 88, "useful_samples": 1024, "total_samples": 1112,
        "start_sample_in_subframe": 0, "start_tc_in_subframe": 0,
    }


def test_actual_slots_differ_at_60khz():
    first = NRCell(subcarrier_spacing_khz=60)
    second = first.with_slot_offset()
    assert first.cp_lengths_samples[0] == 104
    assert first.cp_lengths_samples[14] == 72
    assert first.cp_lengths_samples[28] == 104
    assert (first.samples_per_slot, second.samples_per_slot) == (15376, 15344)
    assert second.slot_start_sample == 15376
    assert first.slot_duration_s > first.nominal_slot_duration_s > second.slot_duration_s
    assert second.symbol_timing(0)["start_tc_in_subframe"] == 492032
    assert second.symbol_timing(0)["cp_samples"] == 72


@pytest.mark.parametrize("scs,cp", [(15, "normal"), (30, "normal"), (60, "normal"),
                                   (120, "normal"), (240, "normal"), (60, "extended")])
def test_all_grid_sizes_preserve_integer_timing(scs, cp):
    """遍历全部 275 个合法宽度，检查物理时间和采样数的守恒关系。"""
    for nrb in range(1, 276):
        cell = NRCell(subcarrier_spacing_khz=scs, cyclic_prefix=cp, n_size_grid=nrb)
        assert cell.n_fft & (cell.n_fft - 1) == 0
        assert cell.n_fft >= cell.n_subcarriers
        assert sum(cell.symbol_lengths_tc) == 1_966_080
        assert sum(cell.symbol_lengths_samples) == cell.samples_per_subframe
        assert all(cp_tc % cell.tc_per_sample == 0 for cp_tc in cell.cp_lengths_tc)
        assert cell.symbol_start_samples[-1] + cell.symbol_lengths_samples[-1] == cell.samples_per_subframe
        assert cell.sample_period_s / cell.tc_s == pytest.approx(cell.tc_per_sample)


def test_extended_cp_sampling():
    cell = NRCell(subcarrier_spacing_khz=60, cyclic_prefix="extended", n_slot=3)
    assert cell.cp_lengths_tc == (8192,) * 48
    assert cell.cp_lengths_samples == (256,) * 48
    assert cell.symbol_lengths_samples == (1280,) * 48
    assert cell.slot_symbol_lengths_samples == (1280,) * 12
    assert cell.samples_per_slot == 15360
    assert cell.slot_start_sample == 46080
    assert cell.symbol_timing(11)["symbol_in_subframe"] == 47


@pytest.mark.parametrize("value", [-1, 14, True, 0.5])
def test_symbol_timing_bounds(value):
    with pytest.raises(TypeError if type(value) is not int else ValueError):
        NRCell().symbol_timing(value)
