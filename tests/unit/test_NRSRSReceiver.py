"""SRS接收机：多用户分离、真实延迟/噪声、不可辨识拒绝与输入约束。"""

from dataclasses import replace

import numpy as np
import pytest

from cell import NRCell
from grid import NRGrid
from srs import NRSRS, NRSRSReceiver


def scene(n_ports=2, *, noise=0.0, two_users=False):
    cell = NRCell(n_size_grid=24, n_rx_antennas=4)
    user = NRSRS(cell, n_ports=n_ports, c_srs=6, n_symbols=4, start_position=3)
    resources = {"A": user}
    if two_users:
        resources["B"] = replace(user, cyclic_shift=2)
    rx = np.zeros((4, 14, 288), dtype=complex)
    truths = {}
    occupied = np.zeros((14, 288), dtype=bool)
    for i, (uid, srs) in enumerate(resources.items()):
        cir = np.zeros((4, n_ports, 8), dtype=complex)
        cir[:n_ports, :, 2+i*3] = np.eye(n_ports)*(1+i)
        truths[uid] = cir
        h = np.einsum("rpd,kd->rpk", cir, np.exp(-2j*np.pi*np.arange(288)[:, None]*np.arange(8)/512))
        grid = NRGrid(cell, n_ports)
        srs.map_to_grid(grid)
        rx += np.einsum("rpk,plk->rlk", h, grid.data)
        occupied |= np.any(grid.occupancy, axis=0)
    rng = np.random.default_rng(123)
    perturbation = (rng.normal(size=rx.shape)+1j*rng.normal(size=rx.shape))*np.sqrt(noise/2)
    return cell, resources, rx+perturbation, ~occupied, truths, perturbation


@pytest.mark.parametrize("ports", [1, 2, 4])
def test_exact_recovery_power_normalization_and_integer_delay(ports):
    cell, resources, rx, muted, truths, _ = scene(ports)
    receiver = NRSRSReceiver(cell)
    result = receiver.estimate(rx, resources, noise_mask=muted)
    user = result["users"]["A"]
    np.testing.assert_allclose(user["cir"], truths["A"], atol=2e-9)
    assert user["status"] == "detected" and user["ri"] == ports
    assert user["delay_samples"] == 2
    assert user["delay_tc"] == 2*cell.tc_per_sample
    assert user["delay_s"] == 2/cell.sample_rate_hz
    assert abs(user["mean_delay_samples"]-2) < 1e-10
    assert result["noise"]["wideband_noise_power"] == 0


def test_overlapping_users_are_jointly_separated():
    cell, resources, rx, muted, truths, _ = scene(two_users=True)
    result = NRSRSReceiver(cell).estimate(rx, resources, noise_mask=muted)
    for uid in resources:
        np.testing.assert_allclose(result["users"][uid]["cir"], truths[uid], atol=1e-8)
    assert result["users"]["A"]["delay_samples"] == 2
    assert result["users"]["B"]["delay_samples"] == 5
    # 完全相同签名的用户不可辨识，不能把同一信号各认领一遍。
    resources["B"] = resources["A"]
    with pytest.raises(ValueError, match="identifiable"):
        NRSRSReceiver(cell).estimate(rx, resources, noise_mask=muted)


def test_muted_noise_is_measured_once_not_from_pilot_mismatch():
    cell, resources, rx, muted, _, actual_noise = scene(noise=.001)
    result = NRSRSReceiver(cell).estimate(rx, resources, noise_mask=muted)
    np.testing.assert_allclose(result["noise"]["wideband_noise_power_per_rx"], np.mean(abs(actual_noise[:, muted])**2, axis=1))
    for rb in range(24):
        mask = muted.copy()
        mask[:, :rb*12] = False
        mask[:, (rb+1)*12:] = False
        np.testing.assert_allclose(result["noise"]["narrowband_noise_power"][rb], np.mean(abs(actual_noise[:, mask])**2))
    result2 = NRSRSReceiver(cell).estimate(rx, resources)
    assert result2["noise"]["method"] == "ls_residual"
    assert abs(result2["noise"]["wideband_noise_power"]-.001) < .0002
    assert result["users"]["A"]["delay_samples"] == 2


def test_known_beta_and_rank_subset():
    cell, resources, rx, muted, truths, _ = scene()
    result = NRSRSReceiver(cell).estimate(rx*.7, resources, noise_mask=muted, betas={"A": .7},
        selection_options={"A": {"max_rank": 1, "allowed_tpmi": {1: [4]}}})
    np.testing.assert_allclose(result["users"]["A"]["cir"], truths["A"], atol=1e-8)
    assert result["users"]["A"]["ri"] == 1 and result["users"]["A"]["tpmi"] == 4


def test_inactive_zero_signal_and_noise_only():
    cell, resources, rx, muted, _, _ = scene()
    resources["off"] = replace(resources["A"], enabled=False)
    receiver = NRSRSReceiver(cell)
    result = receiver.estimate(rx, resources, noise_mask=muted)
    assert result["users"]["off"]["status"] == "inactive"
    result = receiver.estimate(rx*0, resources, noise_mask=muted)
    assert result["users"]["A"]["ri"] is None
    assert result["users"]["A"]["delay_samples"] is None
    assert result["users"]["A"]["snr_db"] is None
    result = receiver.estimate(rx*0, {"off": resources["off"]}, noise_mask=muted)
    assert result["unknown_count"] == 0 and result["design_condition_number"] is None


@pytest.mark.parametrize("kwargs,error", [({"cell": None}, TypeError), ({"n_delay_taps": True}, TypeError),
    ({"n_delay_taps": 0}, ValueError), ({"n_delay_taps": 999}, ValueError),
    ({"max_condition_number": 0}, ValueError), ({"max_condition_number": True}, TypeError),
    ({"first_path_relative_power": 0}, ValueError), ({"first_path_relative_power": 1.1}, ValueError),
    ({"first_path_relative_power": True}, TypeError),
    ({"min_snr_db": float("nan")}, ValueError)])
def test_constructor_validation(kwargs, error):
    with pytest.raises(error):
        NRSRSReceiver(**({"cell": NRCell()} | kwargs))


def test_receive_input_validation_and_insufficient_dof():
    cell, resources, rx, muted, _, _ = scene()
    receiver = NRSRSReceiver(cell)
    for value in (rx[0], rx*np.nan):
        with pytest.raises(ValueError, match="rx_grid"):
            receiver.estimate(value, resources)
    for bad in ({}, [], {"": resources["A"]}, {"A": None}, {"A": replace(resources["A"], cell=replace(cell, n_cell_id=2))}):
        with pytest.raises(ValueError):
            receiver.estimate(rx, bad, noise_mask=muted)
    for betas in ([], {"X": 1}, {"A": -1}, {"A": float("inf")}):
        with pytest.raises(ValueError):
            receiver.estimate(rx, resources, betas=betas, noise_mask=muted)
    with pytest.raises(TypeError):
        receiver.estimate(rx, resources, betas={"A": True}, noise_mask=muted)
    for options in ({"X": {}}, {"A": {"extra": 1}}, {"A": 1}):
        with pytest.raises(ValueError):
            receiver.estimate(rx, resources, selection_options=options, noise_mask=muted)
    with pytest.raises(TypeError):
        receiver.estimate(rx, resources, selection_options=[], noise_mask=muted)
    for mask in (muted.astype(int), muted[0], ~muted, muted & False):
        with pytest.raises(ValueError, match="noise_mask"):
            receiver.estimate(rx, resources, noise_mask=mask)
    with pytest.raises(ValueError, match="ill-conditioned"):
        replace(receiver, max_condition_number=1).estimate(rx, resources, noise_mask=muted)
    with pytest.raises(ValueError, match="degrees of freedom"):
        receiver.estimate(rx*0, {"A": replace(resources["A"], enabled=False)})


def test_bwp_noise_mask_and_unsounded_rb_are_explicit():
    cell = NRCell(n_size_grid=24, bwp_start=2, bwp_size=8)
    resource = NRSRS(cell, frequency_shift=2)
    rx = np.zeros((1, 14, 288), dtype=complex)
    grid = NRGrid(cell)
    resource.map_to_grid(grid)
    rx[:] = grid.data
    mask = np.zeros((14, 288), dtype=bool)
    mask[0, 24:120] = True
    result = NRSRSReceiver(cell, n_delay_taps=1).estimate(rx, {"A": resource}, noise_mask=mask)
    assert np.isnan(result["noise"]["narrowband_noise_power"][0])
    mask[0, 0] = True
    with pytest.raises(ValueError, match="inside BWP"):
        NRSRSReceiver(cell).estimate(rx, {"A": resource}, noise_mask=mask)


def test_first_arrival_and_strongest_path_are_distinct():
    cell, resources, _, muted, _, _ = scene()
    srs = resources["A"]
    grid = NRGrid(cell, srs.n_ports)
    srs.map_to_grid(grid)
    cir = np.zeros((4,2,8),dtype=complex)
    cir[:2,:,1] = np.eye(2)*.5
    cir[:2,:,7] = np.eye(2)
    phase = np.exp(-2j*np.pi*np.arange(288)[:,None]*np.arange(8)/512)
    h = np.einsum("rpd,kd->rpk",cir,phase)
    rx = np.einsum("rpk,plk->rlk",h,grid.data)
    user = NRSRSReceiver(cell).estimate(rx,resources,noise_mask=muted)["users"]["A"]
    assert user["first_path_delay_samples"] == 1
    assert user["delay_samples"] == 7 and user["delay_window_edge"]
    np.testing.assert_allclose(user["mean_delay_samples"],5.8,atol=1e-10)
    np.testing.assert_allclose(user["rms_delay_spread_samples"],2.4,atol=1e-10)


def test_user_power_not_diluted_by_other_users_disjoint_resources():
    cell = NRCell(n_size_grid=24,n_rx_antennas=1)
    a = NRSRS(cell)
    b = replace(a,frequency_shift=12)
    ga,gb = NRGrid(cell),NRGrid(cell)
    a.map_to_grid(ga)
    b.map_to_grid(gb)
    receiver = NRSRSReceiver(cell,n_delay_taps=1)
    one = receiver.estimate(ga.data,{"A":a},noise_mask=~ga.occupancy[0])["users"]["A"]
    two = receiver.estimate(ga.data+.2*gb.data,{"A":a,"B":b},
        noise_mask=~(ga.occupancy[0]|gb.occupancy[0]))["users"]["A"]
    np.testing.assert_allclose([one["signal_power"],two["signal_power"]],[1,1],atol=1e-12)
    np.testing.assert_allclose(one["snr_db"],two["snr_db"],atol=1e-10)


def test_per_user_rsrp_is_separated_while_rssi_includes_overlapping_users():
    cell,resources,rx,muted,_,_=scene(n_ports=1,two_users=True)
    result=NRSRSReceiver(cell).estimate(rx,resources,noise_mask=muted)
    a,b=result["users"]["A"],result["users"]["B"]
    np.testing.assert_allclose([a["rsrp"],b["rsrp"]],[.25,1],atol=1e-10)
    np.testing.assert_allclose(a["rssi"],b["rssi"],atol=1e-12)
    expected=np.sum(abs(rx[:,10:14,:287])**2,axis=2).mean(axis=1)
    np.testing.assert_allclose(a["rssi"],expected.mean(),atol=1e-8)
    np.testing.assert_allclose(a["rssi_per_rx"],expected,atol=1e-8)
    np.testing.assert_allclose(a["rsrp_per_rx"],[1,0,0,0],atol=1e-9)
    np.testing.assert_allclose(a["rsrp_db"],10*np.log10(.25))
    np.testing.assert_allclose(a["rssi_db"],10*np.log10(expected.mean()))
    zero=NRSRSReceiver(cell).estimate(rx*0,resources,noise_mask=muted)["users"]["A"]
    assert zero["rsrp"]==zero["rssi"]==0
    assert zero["rsrp_db"] is zero["rssi_db"] is None


def test_per_user_snr_uses_measured_noise_and_is_consistent_with_rsrp():
    cell,resources,rx,muted,_,_=scene(noise=.001,two_users=True)
    result=NRSRSReceiver(cell).estimate(rx,resources,noise_mask=muted)
    for user in result["users"].values():
        np.testing.assert_allclose(user["snr_db"],10*np.log10(user["rsrp"]/result["noise"]["wideband_noise_power"]))
        assert user["rssi"]>user["rsrp"]
