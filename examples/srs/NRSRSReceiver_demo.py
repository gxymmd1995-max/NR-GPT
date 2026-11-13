"""频域多用户SRS接收：RI/TPMI、PRB/宽带噪声、每用户时延；输出均在本目录。"""

from dataclasses import replace
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from cell import NRCell
from channel import NRChannel
from diagnostics import ExampleLogger
from grid import NRGrid, channel_color
from srs import NRSRS, NRSRSReceiver


def json_value(value):
    """将数组/复数转成可审阅JSON；未观测PRB的NaN写成null，不写非标准JSON。"""
    if isinstance(value, np.ndarray):
        return (
            {"real": value.real.tolist(), "imag": value.imag.tolist()}
            if np.iscomplexobj(value)
            else json_value(value.tolist())
        )
    if isinstance(value, dict):
        return {key: json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    if isinstance(value, (float, np.floating)) and not np.isfinite(value):
        return None
    if isinstance(value, np.generic):
        return value.item()
    return value


def plot_cyclic_shift_windows(rx, resources, delays, n_delay_taps, output):
    """仅诊断本示例的两个独立SRS组：公共IFFT坐标包含CS，各用户CIR已去CS。

    IFFT长度Nfft/K_TC，使横轴一步对应一个NRCell采样点。有限探测带宽产生旁瓣，
    阴影为预期因果FIR窗，不表示窗外能量必为零，也不替代联合LS接收算法。
    """
    groups = [
        ("Shared sequence 17 / comb 2, offset 0", ["UE0", "UE1"]),
        ("Separate sequence 93 / comb 4, offset 1", ["UE2"]),
    ]
    colors = {"UE0": "#0072B2", "UE1": "#D55E00", "UE2": channel_color("SRS")}
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), layout="constrained")
    records = []
    for ax, (title, uids) in zip(axes, groups):
        base = replace(resources[uids[0]], n_ports=1, cyclic_shift=0)
        indices = base.indices().reshape(base.n_symbols, base.sequence_length, 3)
        reference = base.generate().reshape(base.n_symbols, base.sequence_length)
        mixed = rx[:, indices[:, :, 1], indices[:, :, 2]] / reference[None, :, :]
        length = base.cell.n_fft // base.k_tc
        impulse = np.fft.ifft(mixed, n=length, axis=-1)
        power = np.sum(abs(impulse) ** 2, axis=(0, 1))
        ax.plot(
            np.arange(length),
            10 * np.log10(np.maximum(power / power.max(), 1e-8)),
            color="#334155",
            linewidth=1,
        )
        for uid in uids:
            srs = resources[uid]
            for port in range(srs.n_ports):
                cs = (
                    srs.cyclic_shift + srs.max_cyclic_shifts * port // srs.n_ports
                ) % srs.max_cyclic_shifts
                origin = float((-length * cs / srs.max_cyclic_shifts) % length)
                peak = float((origin + delays[uid]) % length)
                ax.axvspan(
                    origin,
                    min(origin + n_delay_taps, length),
                    color=colors[uid],
                    alpha=0.18,
                )
                ax.axvline(peak, color=colors[uid], linestyle="--", linewidth=1)
                ax.text(
                    origin + 0.5,
                    -3,
                    f"{uid} p{port}\nCS={cs}",
                    color=colors[uid],
                    fontsize=9,
                    va="top",
                )
                records.append(
                    {
                        "user": uid,
                        "port": port,
                        "sequence_id": srs.sequence_id,
                        "k_tc": srs.k_tc,
                        "cyclic_shift": cs,
                        "ifft_length": length,
                        "window_origin_samples": origin,
                        "expected_peak_samples": peak,
                        "local_delay_samples": delays[uid],
                    }
                )
        ax.set(
            title=title,
            xlabel="Common IFFT delay coordinate (NRCell samples, includes cyclic shift)",
            ylabel="Relative power (dB)",
            xlim=(0, length - 1),
            ylim=(-50, 2),
        )
        ax.grid(alpha=0.15)
    fig.suptitle(
        "Raw SRS delay windows before cyclic-shift removal | one panel per sequence/comb group"
    )
    fig.supxlabel(
        "TS38.211 V15.2.0 6.4.1.4.2; window origin = (-Nfft/KTC * CS/NcsMax) mod (Nfft/KTC). "
        "Shaded = expected 8-sample FIR windows; finite bandwidth causes sidelobes.",
        fontsize=9,
    )
    for suffix in ("png", "svg"):
        fig.savefig(output / f"NRSRSReceiver_cs_windows.{suffix}", dpi=150)
    plt.close(fig)
    return records


def main(log: ExampleLogger) -> None:
    """构造3用户已知多径和有色AWGN，估计并画实际值/估计值对照。"""
    output = Path(__file__).resolve().parent
    cell = NRCell(n_size_grid=24, n_start_grid=10, n_rx_antennas=4, n_tx_antennas=2)
    base = NRSRS(
        cell, n_ports=2, c_srs=6, n_symbols=4, start_position=3, sequence_id=17
    )
    resources = {
        "UE0": base,
        "UE1": replace(base, cyclic_shift=2),
        "UE2": replace(
            base,
            n_ports=1,
            n_symbols=2,
            start_position=1,
            k_tc=4,
            comb_offset=1,
            sequence_id=93,
        ),
    }
    delays = {"UE0": 3, "UE1": 6, "UE2": 1}
    gains = {
        "UE0": np.array([[1, 0], [0, 1], [0.2, 0.1], [0, 0.3j]]),
        "UE1": np.array([[1, 0.8j], [0.5, 0.4j], [0.1, 0.08j], [0.1j, -0.08]]),
        "UE2": np.array([[0.8], [0.4j], [0.3], [0.1j]]),
    }
    receiver = NRSRSReceiver(cell, n_delay_taps=8)
    rx = np.zeros((4, 14, 288), dtype=complex)
    muted = np.ones((14, 288), dtype=bool)
    stored = {}
    for uid, resource in resources.items():
        cir = np.zeros((4, resource.n_ports, 8), dtype=complex)
        cir[:, :, delays[uid]] = gains[uid]
        if uid == "UE0":
            cir[:, :, 5] = 0.2 * gains[uid]
        h = np.einsum(
            "rpd,kd->rpk",
            cir,
            np.exp(-2j * np.pi * np.arange(288)[:, None] * np.arange(8) / cell.n_fft),
        )
        grid = NRGrid(cell, resource.n_ports)
        resource.map_to_grid(grid)
        rx += np.einsum("rpk,plk->rlk", h, grid.data)
        muted &= ~np.any(grid.occupancy, axis=0)
        stored[f"{uid}_true_cir"] = cir
        stored[f"{uid}_tx_grid"] = grid.data
    # 频域接收机示例：白噪声对样点坐标无依赖，将每PRB的Rx/RE平铺后按SNR加噪。
    # 低SNR的四个PRB演示有色噪声；所有方差由实际无噪接收信号功率派生。
    snr_per_rb = np.full(24, 12.0)
    snr_per_rb[12:16] = 0.0
    variance = np.zeros(24)
    noise = np.zeros_like(rx)
    model = NRChannel(cell)
    for rb, snr in enumerate(snr_per_rb):
        block = rx[:, :, rb * 12 : (rb + 1) * 12].reshape(4, -1)
        _, perturbation = model.add_awgn(block, snr_db=float(snr), seed=20261026 + rb)
        noise[:, :, rb * 12 : (rb + 1) * 12] = perturbation.reshape(4, 14, 12)
        variance[rb] = np.mean(abs(block) ** 2) * 10 ** (-snr / 10)
    rx += noise
    result = receiver.estimate(rx, resources, noise_mask=muted)
    windows = plot_cyclic_shift_windows(
        rx, resources, delays, receiver.n_delay_taps, output
    )
    log.dump_state(cell, "cell")
    log.dump_state(receiver, "receiver")
    for uid in resources:
        log.dump_state(resources[uid], uid)
        user = result["users"][uid]
        log.logger.info(
            "%s: status=%s RI=%s TPMI=%s delay=%s samples / %.6f us / %s Tc SNR=%.3f dB",
            uid,
            user["status"],
            user["ri"],
            user["tpmi"],
            user["delay_samples"],
            user["delay_s"] * 1e6,
            user["delay_tc"],
            user["snr_db"],
        )
        log.logger.info(
            "%s: RSSI=%g (%g dB), RSRP=%g (%g dB)",
            uid,
            user["rssi"],
            user["rssi_db"],
            user["rsrp"],
            user["rsrp_db"],
        )
        stored[f"{uid}_estimated_cir"] = user["cir"]
        stored[f"{uid}_estimated_channel"] = user["channel"]
    np.savez_compressed(
        output / "NRSRSReceiver_data.npz",
        rx_grid=rx,
        noise_grid=noise,
        noise_mask=muted,
        true_noise_variance_per_rb=variance,
        **stored,
    )
    summary = {
        "cell": cell.to_dict(),
        "receiver": {
            "n_delay_taps": 8,
            "min_snr_db": 0,
            "max_condition_number": 1e8,
            "first_path_relative_power": 0.1,
        },
        "resources": {uid: resource.to_dict() for uid, resource in resources.items()},
        "snr_db_per_rb": snr_per_rb,
        "true_delay_samples": delays,
        "true_noise_variance_per_rb": variance,
        "result": result,
        "cyclic_shift_windows": windows,
        "seed": 20261026,
        "scope": "Already OFDM-demodulated frequency samples; delays relative to FFT window, integer FIR grid; no TA command or RF noise in dBm.",
    }
    (output / "NRSRSReceiver_summary.json").write_text(
        json.dumps(json_value(summary), indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), layout="constrained")
    fig.suptitle("SRS uplink receiver | 3 users, 4 Rx branches | R15 codebook RI/TPMI")
    image = axes[0, 0].imshow(
        10 * np.log10(np.mean(abs(rx) ** 2, axis=0).T + 1e-12),
        origin="lower",
        aspect="auto",
        cmap="viridis",
    )
    axes[0, 0].set(
        title="Received power (mean over Rx)",
        xlabel="OFDM symbol",
        ylabel="Carrier-local subcarrier k",
    )
    fig.colorbar(image, ax=axes[0, 0], label="dB, normalized power / RE")
    axes[0, 1].plot(range(24), variance, "k--", label="Injected expected noise")
    axes[0, 1].plot(
        range(24),
        result["noise"]["narrowband_noise_power"],
        "o-",
        color=channel_color("SRS"),
        label="Measured muted-RE noise",
    )
    axes[0, 1].axhline(
        result["noise"]["wideband_noise_power"], color="#0072B2", label="Wideband mean"
    )
    axes[0, 1].set(
        title="Narrowband per PRB / wideband noise",
        xlabel="Carrier-local RB",
        ylabel="Complex noise power / RE / Rx",
    )
    axes[0, 1].legend(fontsize=8)
    colors = ["#0072B2", "#D55E00", channel_color("SRS")]
    for uid, color in zip(resources, colors):
        power = result["users"][uid]["delay_power"]
        axes[1, 0].plot(
            np.arange(8),
            power / max(power),
            "o-",
            color=color,
            label=f"{uid}, true peak={delays[uid]}",
        )
    axes[1, 0].set(
        title="Separated per-user CIR (cyclic shifts removed)",
        xlabel="Per-user relative delay (NRCell samples)",
        ylabel="Normalized noise-debiased tap power",
        xticks=range(8),
    )
    axes[1, 0].legend(fontsize=8)
    rows = []
    for uid in resources:
        user = result["users"][uid]
        rows.append(
            [
                uid,
                user["ri"],
                user["tpmi"],
                f"{user['delay_samples']}",
                f"{user['snr_db']:.2f}",
                f"{user['rssi_db']:.2f}",
                f"{user['rsrp_db']:.2f}",
            ]
        )
    axes[1, 1].axis("off")
    axes[1, 1].table(
        cellText=rows,
        colLabels=[
            "User",
            "RI",
            "TPMI",
            "Peak samples",
            "SNR dB",
            "RSSI dB",
            "RSRP dB",
        ],
        loc="center",
        cellLoc="center",
    )
    axes[1, 1].set_title("Measured uplink recommendations / timing")
    fig.supxlabel(
        "TS 38.211 V15.2.0 SRS / PUSCH codebooks. Joint finite-FIR LS, noise estimates and MI selection are project receiver algorithms.",
        fontsize=9,
    )
    for suffix in ("png", "svg"):
        fig.savefig(output / f"NRSRSReceiver_overview.{suffix}", dpi=150)
    plt.close(fig)
    log.logger.info(
        "Wideband noise=%.8g; design condition=%.5g; outputs in %s",
        result["noise"]["wideband_noise_power"],
        result["design_condition_number"],
        output,
    )


if __name__ == "__main__":
    with ExampleLogger(__file__) as run:
        main(run)
