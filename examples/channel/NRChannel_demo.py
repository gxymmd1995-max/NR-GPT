"""SRS时域收发：OFDM/符号相位 -> TA -> 传播延迟 -> CFO/AWGN -> 校正 -> 接收测量。"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from cell import NRCell
from common import NROFDM, NRPhaseRotation
from channel import NRChannel
from diagnostics import ExampleLogger
from grid import NRGrid, channel_color
from srs import NRSRS, NRSRSReceiver


def main(log):
    """已知CFO校正示例；TA直接配置4采样点，物理延迟7点，残余3点。"""
    output = Path(__file__).resolve().parent
    cell = NRCell(n_size_grid=24, n_rx_antennas=2, n_tx_antennas=2)
    srs = NRSRS(cell, n_ports=2, c_srs=6, n_symbols=4, start_position=3, sequence_id=42)
    tx_grid = NRGrid(cell, 2)
    srs.map_to_grid(tx_grid)
    ofdm = NROFDM(cell, 3500000123)
    channel = NRChannel(cell)
    tx_wave = ofdm.modulate(tx_grid.data)
    ta_samples = 4  # 单位：采样点；在当前配置下等效于相对TA命令32。
    advanced = channel.timing_advance(tx_wave, ta_samples)
    gain = np.array([[1, 0.1j], [0.2, 0.9]], complex)
    path_delay = 7
    delayed = channel.timing_advance(gain @ advanced, -path_delay)
    cfo_hz = 1234
    phase = 0.37
    offset_wave = channel.frequency_offset(delayed, cfo_hz, phase)
    snr_db = 20.0
    time_noise = np.mean(abs(offset_wave) ** 2, axis=1) * 10 ** (-snr_db / 10)
    target_re_noise = float(time_noise.mean() * cell.n_fft)
    received, noise = channel.add_awgn(offset_wave, snr_db=snr_db, seed=20261026)
    corrected = channel.frequency_offset(received, -cfo_hz, -phase)
    raw_grid = ofdm.demodulate(received, 0.5)
    rx_grid = ofdm.demodulate(corrected, 0.5)
    residual_delay = path_delay - ta_samples
    ideal = (
        np.einsum("rp,plk->rlk", gain, tx_grid.data)
        * NRPhaseRotation(cell).timing_phasors(residual_delay)[None, None, :]
    )
    active = np.any(tx_grid.occupancy, axis=0)
    energy = float(np.sum(abs(ideal[:, active]) ** 2))
    evm_raw = float(
        np.sqrt(np.sum(abs(raw_grid[:, active] - ideal[:, active]) ** 2) / energy)
    )
    evm_corrected = float(
        np.sqrt(np.sum(abs(rx_grid[:, active] - ideal[:, active]) ** 2) / energy)
    )
    receiver = NRSRSReceiver(cell)
    result = receiver.estimate(rx_grid, {"UE0": srs}, noise_mask=~active)
    user = result["users"]["UE0"]
    log.dump_state(cell, "cell")
    log.dump_state(ofdm, "ofdm")
    log.dump_state(channel, "channel")
    log.dump_state(receiver, "receiver")
    summary = {
        "cell": cell.to_dict(),
        "srs": srs.to_dict(),
        "carrier_frequency_hz": ofdm.carrier_frequency_hz,
        "ta_unit": "samples",
        "ta_command": 32,
        "ta_samples": ta_samples,
        "path_delay_samples": path_delay,
        "true_residual_delay_samples": residual_delay,
        "frequency_offset_hz": cfo_hz,
        "initial_phase_rad": phase,
        "seed": 20261026,
        "cp_fraction": 0.5,
        "snr_db": snr_db,
        "time_noise_power_per_rx": time_noise.tolist(),
        "target_re_noise_power": target_re_noise,
        "measured_re_noise_power": result["noise"]["wideband_noise_power"],
        "evm_before_cfo_correction": evm_raw,
        "evm_after_cfo_correction": evm_corrected,
        "estimated_delay_samples": user["delay_samples"],
        "estimated_delay_tc": user["delay_tc"],
        "ri": user["ri"],
        "tpmi": user["tpmi"],
        "srs_snr_db": user["snr_db"],
        "rssi": user["rssi"],
        "rsrp": user["rsrp"],
        "known_cfo_correction": True,
        "note": "CFO is explicitly known; no blind CFO/TA estimator or TAG activation scheduler.",
    }
    (output / "NRChannel_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    np.savez_compressed(
        output / "NRChannel_data.npz",
        tx_grid=tx_grid.data,
        tx_waveform=tx_wave,
        advanced_waveform=advanced,
        delayed_waveform=delayed,
        offset_waveform=offset_wave,
        received_waveform=received,
        noise_waveform=noise,
        corrected_waveform=corrected,
        raw_grid=raw_grid,
        recovered_grid=rx_grid,
        ideal_grid=ideal,
        delay_power=user["delay_power"],
    )
    log.logger.info(
        "TA=%d samples, path=%d samples, measured residual=%s samples; CFO=%g Hz; RI/TPMI=%s/%s",
        ta_samples,
        path_delay,
        user["delay_samples"],
        cfo_hz,
        user["ri"],
        user["tpmi"],
    )
    log.logger.info(
        "EVM before/after CFO correction=%g/%g; measured RE noise=%g",
        evm_raw,
        evm_corrected,
        result["noise"]["wideband_noise_power"],
    )
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), layout="constrained")
    fig.suptitle("SRS waveform chain | NR OFDM + symbol phase | TA / CFO / AWGN")
    axes[0, 0].plot(abs(received[0]), color=channel_color("SRS"))
    axes[0, 0].set(
        title="Received SRS waveform, Rx0", xlabel="Slot sample", ylabel="Magnitude"
    )
    axes[0, 1].plot(
        range(14),
        np.angle(NRPhaseRotation(cell, ofdm.carrier_frequency_hz).symbol_phasors()),
        "o-",
    )
    axes[0, 1].set(
        title="Per-symbol NR phase compensation",
        xlabel="Slot symbol",
        ylabel="Wrapped phase (rad)",
    )
    axes[1, 0].bar(
        ["Before CFO correction", "Known CFO corrected"],
        [evm_raw * 100, evm_corrected * 100],
        color=["#94A3B8", channel_color("SRS")],
    )
    axes[1, 0].set(
        title=f"Injected CFO {cfo_hz} Hz / phase {phase} rad",
        ylabel="RMS EVM (%) against known delayed MIMO grid",
    )
    axes[1, 1].stem(np.arange(8), user["delay_power"])
    axes[1, 1].axvline(
        residual_delay,
        color="#D55E00",
        linestyle="--",
        label="True residual = path - TA",
    )
    axes[1, 1].set(
        title=f"TA {ta_samples} samples, path {path_delay}, measured {user['delay_samples']} samples | RI={user['ri']} TPMI={user['tpmi']}",
        xlabel="Delay sample",
        ylabel="Estimated tap power",
    )
    axes[1, 1].legend(fontsize=8)
    fig.supxlabel(
        "R15: TS38.211 5.3.1/5.4; TS38.213 4.2. AWGN/CFO are project models; known CFO correction; integer TA; no waveform wrap.",
        fontsize=9,
    )
    for suffix in ("png", "svg"):
        fig.savefig(output / f"NRChannel_overview.{suffix}", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    with ExampleLogger(__file__) as run:
        main(run)
