"""真实时域SRS链路：TA/传播延迟/CFO/AWGN后，OFDM解调连接现有接收测量。"""

import numpy as np

from cell import NRCell
from common import NROFDM, NRPhaseRotation
from channel import NRChannel
from grid import NRGrid
from srs import NRSRS, NRSRSReceiver


def test_srs_waveform_ta_cfo_noise_and_receiver():
    cell = NRCell(n_size_grid=24, n_rx_antennas=2)
    srs = NRSRS(cell, n_ports=2, c_srs=6, n_symbols=4, start_position=3)
    grid = NRGrid(cell, 2)
    srs.map_to_grid(grid)
    ofdm = NROFDM(cell, 3500000123)
    channel = NRChannel(cell)
    tx = ofdm.modulate(grid.data)
    advanced = channel.timing_advance(tx, channel.ta_command_samples(32))
    delayed = channel.timing_advance(advanced, -7)
    ideal = grid.data * NRPhaseRotation(cell).timing_phasors(3)[None, None, :]
    np.testing.assert_allclose(ofdm.demodulate(delayed, 0.5), ideal, atol=2e-12)
    noisy, _ = channel.add_awgn(
        channel.frequency_offset(delayed, 1234, 0.37), snr_db=20, seed=7
    )
    rx = ofdm.demodulate(channel.frequency_offset(noisy, -1234, -0.37), 0.5)
    raw = ofdm.demodulate(noisy, 0.5)
    mask = np.any(grid.occupancy, axis=0)
    evm = np.linalg.norm((rx - ideal)[:, mask]) / np.linalg.norm(ideal[:, mask])
    assert evm < 0.1
    assert np.linalg.norm((raw - ideal)[:, mask]) > 10 * np.linalg.norm(
        (rx - ideal)[:, mask]
    )
    result = NRSRSReceiver(cell).estimate(rx, {"UE0": srs}, noise_mask=~mask)
    assert result["users"]["UE0"]["delay_samples"] == 3
    assert result["users"]["UE0"]["ri"] == 2
    np.testing.assert_allclose(
        result["noise"]["wideband_noise_power"],
        float(np.mean(abs(delayed) ** 2) * 0.01 * cell.n_fft),
        rtol=0.1,
    )
