"""三UE同频同符号F0：完整候选移位集合正交，独立时域信道后叠加，再分用户检测。"""

import json
from pathlib import Path

import numpy as np

from cell import NRCell
from channel import NRChannel
from diagnostics import ExampleLogger, NRPlotConfig, NRStagePlotter
from pucch import NRPUCCH0, NRPUCCH0Transmitter, NRPUCCH0Receiver


def run_case(
    name="all_active",
    active_users=("UE0", "UE1", "UE2"),
    *,
    initial_shifts=(0, 2, 4),
    snr_db=-5.0,
    detection_threshold=0.15,
    cyclic_prefix="normal",
    subcarrier_spacing_khz=30,
    plot_config=None,
):
    """纯数值/内存案例，不写文件；相同根/Gold、单RB/符号、1bit HARQ，SR未配置。

    三个复信道均为RB内平坦，公共已知净延迟3采样点、CFO731Hz。接收机不知道active_users。
    多用户总能量进入归一化分母，故显式使用工程门限.15，不沿用单用户默认.42。
    """
    cell = NRCell(
        n_cell_id=17,
        n_size_grid=6,
        n_start_grid=10,
        bwp_start=11,
        bwp_size=4,
        n_rx_antennas=2,
        n_slot=3,
        cyclic_prefix=cyclic_prefix,
        subcarrier_spacing_khz=subcarrier_spacing_khz,
    )
    ids = ("UE0", "UE1", "UE2")
    bits = ((0,), (1,), (0,))
    gains = np.array([[1, 0.3 + 0.5j, -0.4j], [0.3j, 0.7, 0.6 + 0.5j]])
    config = NRPlotConfig() if plot_config is None else plot_config
    plotter = NRStagePlotter(config)
    resources = {
        uid: NRPUCCH0(
            cell,
            prb=0,
            start_symbol=8,
            n_symbols=2,
            second_hop_prb=3,
            initial_cyclic_shift=initial_shifts[i],
            hopping_id=731,
            group_hopping="enable",
        )
        for i, uid in enumerate(ids)
    }
    receivers = {
        uid: NRPUCCH0Receiver(resource, 1, False, 3500000123, detection_threshold)
        for uid, resource in resources.items()
    }
    allocation = NRPUCCH0Receiver.validate_cyclic_shift_group(receivers)
    channel = NRChannel(cell)
    mixed = np.zeros((2, cell.samples_per_slot), complex)
    stored = {}
    for i, uid in enumerate(ids):
        plotter.prefix = f"{name}.{uid}"
        sent = NRPUCCH0Transmitter(resources[uid], 3500000123).transmit(
            bits[i], plotter=plotter
        )
        advanced = channel.timing_advance(sent["waveform"], 2)
        spatial = (
            gains[:, i, None] * advanced
            if uid in active_users
            else np.zeros_like(mixed)
        )
        path = channel.timing_advance(spatial, -5)
        offset = channel.frequency_offset(path, 731, 0.23)
        plotter.record(
            "channel.individual_waveform",
            offset,
            title=f"{uid}: own gain, net delay=3, CFO=731 Hz",
        )
        mixed += offset
        stored[f"{uid}_tx_waveform"] = sent["waveform"]
        stored[f"{uid}_channel_waveform"] = offset
    received, noise = channel.add_awgn(mixed, snr_db=snr_db, seed=20261027)
    results = {}
    for uid, receiver in receivers.items():
        plotter.prefix = f"{name}.{uid}"
        results[uid] = receiver.receive(
            received,
            known_frequency_offset_hz=731,
            known_initial_phase_rad=0.23,
            known_delay_samples=3,
            cp_fraction=0.5,
            plotter=plotter,
        )
    references = []
    labels = []
    for uid, receiver in receivers.items():
        for bit in (0, 1):
            references.append(resources[uid].generate([bit]))
            labels.append(f"{uid} ACK{bit}")
    reference = np.array(references)
    gram = np.abs(reference @ reference.conj().T) / reference.shape[1]
    plotter.prefix = f"{name}.summary"
    plotter.record(
        "candidate_gram",
        np.where(gram < 1e-12, 0, gram)[None, :, :],
        kind="grid",
        title="All legal candidate references: normalized Gram magnitude",
        xlabel="Candidate index",
        ylabel="Candidate index",
    )
    plotter.record(
        "mixed_waveform", received, title="Three UE waveforms superposed before AWGN"
    )
    plotter.record(
        "user_metrics",
        [results[uid]["metric"] for uid in ids] + [detection_threshold],
        kind="metric",
        title="Per-UE winner score uses total mixed energy",
        xlabel="UE / threshold",
        ylabel="Normalized correlation power",
        labels=[*ids, "threshold"],
    )
    summary = {
        "name": name,
        "cell": cell.to_dict(),
        "active_users": list(active_users),
        "initial_cyclic_shifts": list(initial_shifts),
        "candidate_shift_sets": allocation,
        "snr_db": snr_db,
        "detection_threshold": detection_threshold,
        "true_harq_ack": {uid: list(bits[i]) for i, uid in enumerate(ids)},
        "common_net_delay_samples": 3,
        "common_cfo_hz": 731,
        "initial_phase_rad": 0.23,
        "rx_gain_real": gains.real.tolist(),
        "rx_gain_imag": gains.imag.tolist(),
        "candidate_labels": labels,
        "candidate_gram": gram.tolist(),
        "max_candidate_orthogonality_error": float(
            np.max(abs(gram - np.eye(len(labels))))
        ),
        "users": {
            uid: {
                key: result[key]
                for key in (
                    "detected",
                    "status",
                    "harq_ack",
                    "sr",
                    "m_cs",
                    "metric",
                    "candidates",
                )
            }
            for uid, result in results.items()
        },
        "plot_stages": list(plotter.stages),
        "scope": "Known shared timing/CFO, flat per-UE gains; orthogonal CDM allocation, no joint multiuser equalizer/SIC.",
    }
    stored.update(
        mixed_noiseless=mixed, received_waveform=received, noise_waveform=noise
    )
    for uid, result in results.items():
        stored[f"{uid}_correlation_symbols"] = result["correlation_symbols"]
        stored[f"{uid}_candidate_correlation_symbols"] = result[
            "candidate_correlation_symbols"
        ]
    return summary, stored, results, plotter


def main(log, plot_config=None):
    """两个案例：3UE同时发送、UE2不发送；仅保存数值JSON/NPZ，图像直接显示。"""
    output = Path(__file__).resolve().parent
    config = (
        NRPlotConfig(
            enabled=True,
            stages=(
                "all_active.*.rx.candidate_metrics",
                "all_active.*.rx.correlated_constellation",
                "all_active.summary.*",
            ),
        )
        if plot_config is None
        else plot_config
    )
    summaries = []
    arrays = {}
    for name, active in [
        ("all_active", ("UE0", "UE1", "UE2")),
        ("UE2_dtx", ("UE0", "UE1")),
    ]:
        summary, stored, results, plotter = run_case(name, active, plot_config=config)
        summaries.append(summary)
        arrays.update({f"{name}_{key}": value for key, value in stored.items()})
        for uid, result in results.items():
            log.logger.info(
                "%s %s initialCS=%s ACK=%s status=%s score=%.6f",
                name,
                uid,
                summary["initial_cyclic_shifts"][int(uid[-1])],
                result["harq_ack"],
                result["status"],
                result["metric"],
            )
        plotter.show()
    data = {"cases": summaries, "seed": 20261027, "saved_images": False}
    (output / "NRPUCCH0_multiuser_summary.json").write_text(
        json.dumps(data, indent=2) + "\n", encoding="utf-8"
    )
    np.savez_compressed(output / "NRPUCCH0_multiuser_data.npz", **arrays)
    return data


if __name__ == "__main__":
    plot_config = NRPlotConfig(
        enabled=True,
        stages=(
            "all_active.*.rx.candidate_metrics",
            "all_active.*.rx.correlated_constellation",
            "all_active.summary.*",
        ),
    )
    with ExampleLogger(__file__) as run:
        main(run, plot_config)
    if plot_config.enabled:
        import matplotlib.pyplot as plt

        plt.show()
