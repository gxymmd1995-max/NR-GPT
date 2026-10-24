"""运行后在本目录生成 NRCell_timing.png/.svg：FFT、CP 和精确时序。"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from cell import NRCell
from diagnostics import ExampleLogger


def main(log: ExampleLogger) -> None:
    """展示 FFT 选择规则及普通 CP 时序；所有数值从 NRCell 获取。"""
    cell = NRCell()
    log.dump_state(cell, "cell_30khz")
    fig, axes = plt.subplots(3, 1, figsize=(11, 10), layout="constrained")
    fig.get_layout_engine().set(rect=(0, 0.035, 1, 0.965))
    fig.suptitle(f"NRCell timing | Tc={cell.tc_s * 1e9:.9f} ns | Ts=64Tc\n"
                 f"52 RB / 30 kHz: FFT={cell.n_fft}, Fs={cell.sample_rate_hz / 1e6:.2f} MHz, "
                 f"one sample={cell.tc_per_sample}Tc", fontsize=14)
    indices = range(cell.symbols_per_subframe)
    axes[0].bar(indices, [cell.n_fft] * cell.symbols_per_subframe, color="#93C5FD", label="Useful part: 1024 samples")
    axes[0].bar(indices, cell.cp_lengths_samples, bottom=cell.n_fft, color="#10B981", label="CP: 72 / 88 samples")
    axes[0].set(xlabel="Symbol index within 1 ms subframe", ylabel="Samples including CP",
                title="Normal CP: long CP at symbols 0 and 14 (30 kHz)")
    axes[0].set_ylim(0, 1400)
    axes[0].legend(ncols=2, loc="upper right")
    mu2 = NRCell(subcarrier_spacing_khz=60)
    log.dump_state(mu2, "cell_60khz")
    slots = [mu2.with_slot_offset(i) for i in range(mu2.slots_per_subframe)]
    axes[1].bar(range(4), [c.slot_duration_s * 1e6 for c in slots], color="#2563EB", width=0.6)
    for index, slot in enumerate(slots):
        axes[1].text(index, max(slot.slot_duration_s * 1e6 + 0.03, 250.1),
                     f"{slot.samples_per_slot} samples\n{slot.slot_duration_s * 1e6:.6f} us", ha="center", va="bottom", fontsize=10)
    axes[1].axhline(250, color="#DC2626", linestyle="--", label="Nominal: 250 us")
    axes[1].set(xlabel="Slot index within subframe", ylabel="Actual slot duration (us)", ylim=(249, 251),
                title="60 kHz normal CP: actual slot lengths alternate; total = 1 ms", xticks=range(4))
    axes[1].legend(loc="lower right")
    widths = list(range(1, 276))
    axes[2].step(widths, [NRCell(n_size_grid=n).n_fft for n in widths], where="mid", color="#047857", label="Selected FFT")
    axes[2].plot(widths, [12 * n for n in widths], color="#94A3B8", label="Frequency REs per symbol = 12 * RB count")
    axes[2].set_yscale("log", base=2)
    axes[2].set(xlabel="Carrier grid size (RB)", ylabel="FFT / subcarriers (log2 scale)",
                title="Platform policy: max(128, next power of two of 12 * RB)", yticks=[16, 64, 128, 256, 512, 1024, 2048, 4096])
    axes[2].set_yticklabels(["16", "64", "128", "256", "512", "1024", "2048", "4096"])
    axes[2].legend()
    fig.text(0.5, 0.008, "Tc / Ts: TS 38.211 V15.2.0 4.1; frame: 4.3.1-2; CP / useful duration: 5.3.1. FFT size is a platform policy.",
             ha="center", fontsize=9)
    output = Path(__file__).resolve().parent
    for suffix in ("png", "svg"):
        fig.savefig(output / f"NRCell_timing.{suffix}", dpi=150)
    plt.close(fig)
    log.logger.info("Saved timing PNG/SVG in %s", output)


if __name__ == "__main__":
    with ExampleLogger(__file__) as run:
        main(run)
