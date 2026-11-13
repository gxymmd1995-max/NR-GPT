"""Generate documentation figures from actual resource indices (fixed R15 implementation).

Run with --save to export PNGs beside each module's examples; default only shows.
Coordinates are slot-local symbols and carrier-local subcarriers. Colors follow
src/grid/channel_colors.py. These educational plots are not MATLAB references.
"""

import argparse
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch
from cell import NRCell
from grid.channel_colors import channel_color

ROOT = Path(__file__).resolve().parents[1]
CONFIGS = {
    "NRPUCCH0": ("pucch", [{}, dict(n_symbols=2, prb=2, second_hop_prb=20)]),
    "NRPUCCH1": ("pucch", [{}, dict(start_symbol=2, n_symbols=4, prb=3)]),
    "NRPUCCH2": ("pucch", [{}, dict(n_prbs=4, n_symbols=2, prb=2, second_hop_prb=20)]),
    "NRPUCCH3": ("pucch", [{}, dict(n_prbs=2, additional_dmrs=True)]),
    "NRPUCCH4": ("pucch", [{}, dict(spreading_factor=4, additional_dmrs=True)]),
    "NRPUSCH": ("pusch", [{}, dict(n_layers=2, dmrs_additional_position=1)]),
    "NRPDSCH": ("pdsch", [{}, dict(n_layers=2, dmrs_additional_position=1)]),
    "NRPDCCH": ("pdcch", [{}, dict(aggregation_level=4)]),
    "NRSRS": ("srs", [{}, dict(n_symbols=4, start_position=3, k_tc=4)]),
    "NRSSB": ("ssb", [{}, dict(start_symbol=6, start_subcarrier=48)]),
}


def allocation(resource, name):
    """Return integer [symbol,k] categories; merge layer coordinates, not powers."""
    a = np.zeros((resource.cell.symbols_per_slot, resource.cell.n_subcarriers), int)
    if name == "NRSSB":
        a[
            resource.start_symbol : resource.start_symbol + 4,
            resource.start_subcarrier : resource.start_subcarrier + 240,
        ] = 5
        for kind, code in [("pbch", 1), ("dmrs", 2), ("pss", 3), ("sss", 4)]:
            idx = resource.indices(kind)
            a[idx[:, 1], idx[:, 2]] = code
    else:
        idx = resource.indices()
        a[idx[:, 1], idx[:, 2]] = 1
        if name == "NRPUCCH1":
            a[
                resource.start_symbol : resource.start_symbol + resource.n_symbols : 2
            ] *= 2
        elif name not in ("NRPUCCH0", "NRSRS"):
            idx = resource.indices(True)
            a[idx[:, 1], idx[:, 2]] = 2
    return a


def finish(fig, module, filename, save):
    if save:
        target = ROOT / module / filename
        fig.savefig(target, dpi=150, facecolor="white")
        plt.close(fig)
        print(target.relative_to(ROOT.parent))


def resource_figure(name, module, variants, save):
    cls = getattr(__import__(module, fromlist=[name]), name)
    cell = NRCell(n_size_grid=52, subcarrier_spacing_khz=30)
    resources = [cls(cell, **v) for v in variants]
    arrays = [allocation(r, name) for r in resources]
    label = "PUCCH" if module == "pucch" else module.upper()
    cmap = ListedColormap(
        [
            channel_color("FREE"),
            channel_color(label),
            channel_color("DMRS"),
            channel_color("PSS"),
            channel_color("SSS"),
            channel_color("RESERVED"),
        ]
    )
    norm = BoundaryNorm(np.arange(-0.5, 6), cmap.N)
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), layout="constrained")
    fig.suptitle(
        f"{name}：真实资源索引与配置对照 | 52 RB / 30 kHz / 普通 CP", fontsize=16
    )
    for i in range(2):
        ax = axes[0, i]
        ax.imshow(
            arrays[i].T,
            origin="lower",
            aspect="auto",
            interpolation="nearest",
            cmap=cmap,
            norm=norm,
            extent=(-0.5, 13.5, -0.5, cell.n_subcarriers - 0.5),
        )
        text = (
            "默认配置"
            if not variants[i]
            else ", ".join(f"{k}={v}" for k, v in variants[i].items())
        )
        ax.set_title(f"配置 {i+1}：{text}", fontsize=10, wrap=True)
        ax.set(
            xlabel="slot 内 OFDM 符号号", ylabel="载波局部子载波 k", xticks=range(14)
        )
    a = arrays[0]
    ks = np.where(a.any(axis=0))[0]
    lo = int(ks.min())
    hi = min(cell.n_subcarriers, lo + (240 if name == "NRSSB" else 24))
    ax = axes[1, 0]
    ax.imshow(
        a[:, lo:hi].T,
        origin="lower",
        aspect="auto",
        interpolation="nearest",
        cmap=cmap,
        norm=norm,
        extent=(-0.5, 13.5, lo - 0.5, hi - 0.5),
    )
    ax.set(
        title="配置 1 细节：DMRS / 数据 / 梳齿（按 RE 分类）",
        xlabel="slot 内 OFDM 符号号",
        ylabel="载波局部子载波 k",
        xticks=range(14),
    )
    if hi - lo <= 24:
        ax.set_yticks(np.arange(lo - 0.5, hi, 1), minor=True)
        ax.set_xticks(np.arange(-0.5, 14, 1), minor=True)
        ax.grid(which="minor", color="#CBD5E1", linewidth=0.35)
    ax = axes[1, 1]
    starts = (
        np.r_[0, np.cumsum(cell.slot_symbol_lengths_samples)]
        / cell.sample_rate_hz
        * 1e6
    )
    for row, a in enumerate(arrays):
        for l in range(14):
            active = a[l].any()
            color = channel_color(label) if active else "#E2E8F0"
            ax.broken_barh(
                [(starts[l], starts[l + 1] - starts[l])],
                (row - 0.28, 0.56),
                facecolors=color,
                edgecolors="white",
            )
            if active:
                ax.text(
                    (starts[l] + starts[l + 1]) / 2,
                    row,
                    str(l),
                    ha="center",
                    va="center",
                    fontsize=8,
                )
    ax.set(
        xlabel="相对当前 slot 起点 / 微秒（包含各符号 CP）",
        title="时间外框：彩色段为有资源的符号；段内数字为符号号",
        yticks=[0, 1],
        yticklabels=["配置 1", "配置 2"],
        xlim=(0, starts[-1]),
        ylim=(-0.6, 1.6),
    )
    ax.grid(axis="x", alpha=0.2)
    items = [("未分配", "FREE"), ("信号 / 数据", label)]
    if any(np.any(a == 2) for a in arrays):
        items.append(("DMRS", "DMRS"))
    if name == "NRSSB":
        items += [("PSS", "PSS"), ("SSS", "SSS"), ("SSB 保留零 RE", "RESERVED")]
    axes[1, 0].legend(
        handles=[Patch(color=channel_color(c), label=t) for t, c in items],
        loc="upper center",
        bbox_to_anchor=(0.5, -0.18),
        ncol=3,
        fontsize=9,
    )
    finish(fig, module, name + "_documentation.png", save)


def prach_figure(save):
    from prach import NRPRACH, NRPRACHTransmitter, NRPRACHReceiver
    from channel import NRChannel

    cell = NRCell(n_size_grid=52, subcarrier_spacing_khz=30)
    r = NRPRACH(cell, guard_samples=32)
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), layout="constrained")
    fig.suptitle("PRACH A1 / RA 15 kHz：序列、频率、时间与三前导相关", fontsize=16)
    ax = axes[0, 0]
    x = r.sequence(1)
    ax.plot(x.real[:40], label="实部")
    ax.plot(x.imag[:40], label="虚部")
    ax.plot(abs(x[:40]), "--", label="模长 = 1")
    ax.set(
        title="前导 1：ZC 序列前 40 点（不是发送采样点）",
        xlabel="ZC 序列索引",
        ylabel="归一化幅度",
    )
    ax.legend()
    ax = axes[0, 1]
    spec = np.fft.fftshift(r.spectrum(1))
    f = (np.arange(r.n_fft) - r.n_fft // 2) * r.subcarrier_spacing_khz / 1000
    ax.plot(f, abs(spec), color=channel_color("PRACH"))
    ax.axvspan(
        -9.36, -7.2, alpha=0.12, color=channel_color("PRACH"), label="6 UL RB 分配外框"
    )
    ax.set(
        title="139 个非零频率系数；独立 PRACH FFT = 2048",
        xlabel="相对网格中心 / MHz",
        ylabel="DFT 系数模长",
        xlim=(-10, -6.5),
    )
    ax.legend()
    ax = axes[1, 0]
    edges = [
        0,
        r.cp_samples,
        r.cp_samples + r.n_fft,
        r.active_samples,
        r.waveform_samples,
    ]
    for i, title in enumerate(["CP", "周期 0", "周期 1", "guard"]):
        ax.broken_barh(
            [
                (
                    edges[i] / cell.sample_rate_hz * 1e6,
                    (edges[i + 1] - edges[i]) / cell.sample_rate_hz * 1e6,
                )
            ],
            (0, 1),
            facecolors=["#94A3B8", channel_color("PRACH"), "#0072B2", "#E2E8F0"][i],
            edgecolors="white",
        )
        if i < 3:
            ax.text(
                (edges[i] + edges[i + 1]) / 2 / cell.sample_rate_hz * 1e6,
                0.5,
                f"{title}\n{edges[i+1]-edges[i]} 点",
                ha="center",
                va="center",
            )
    ax.set(
        title="一次 CP + 两个有效周期 + 尾部静默 32 点",
        xlabel="相对捕获起点 / 微秒",
        yticks=[],
        ylim=(-0.1, 1.1),
    )
    ax = axes[1, 1]
    y = np.zeros((1, r.waveform_samples), complex)
    for index, delay in [(0, 3), (1, 7), (2, 12)]:
        wave = NRPRACHTransmitter(r).transmit(index)["waveform"]
        y += NRChannel(cell).timing_advance(wave, -delay)
    out = NRPRACHReceiver(r, preamble_indices=(0, 1, 2)).receive(y)
    for i, delay in enumerate([3, 7, 12]):
        ax.plot(
            out["delay_axis_samples"],
            out["delay_profiles"][i],
            "o-",
            label=f"前导 {i}，实际延迟 {delay} 点",
        )
    ax.set(
        title="各候选独立匹配后的局部延迟曲线（无噪声示例）",
        xlabel="接收采样点延迟 d",
        ylabel="相对混合接收能量的相关分数",
    )
    ax.legend()
    ax.grid(alpha=0.2)
    finish(fig, "prach", "NRPRACH_documentation.png", save)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--save", action="store_true", help="explicitly export documentation PNGs"
    )
    args = parser.parse_args()
    plt.rcParams.update(
        {
            "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
            "axes.unicode_minus": False,
            "font.size": 10,
        }
    )
    for name, (module, variants) in CONFIGS.items():
        resource_figure(name, module, variants, args.save)
    prach_figure(args.save)
    if not args.save:
        plt.show()


if __name__ == "__main__":
    main()
