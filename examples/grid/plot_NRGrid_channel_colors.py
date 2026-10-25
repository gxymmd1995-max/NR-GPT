"""生成同级信道配色图与 JSON；仅展示颜色，不声称实现各物理信道。"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from diagnostics import ExampleLogger
from grid import CHANNEL_COLORS, channel_color


def main(log: ExampleLogger) -> None:
    """分组显示 DL、UL 和同步/参考信号的固定颜色，不构造虚假的信道波形。"""
    rows = [
        ("Downlink channels / block", ("SSB", "PDCCH", "PDSCH")),
        ("Uplink channels / signal", ("PUSCH", "PUCCH", "PRACH", "SRS")),
        ("Synchronization / reference signals", ("PSS", "SSS", "PBCH", "DMRS", "PTRS", "CSI_RS")),
    ]
    fig, axes = plt.subplots(3, 1, figsize=(12, 6), layout="constrained")
    fig.get_layout_engine().set(rect=(0, 0.055, 1, 0.945))
    fig.suptitle("NRGrid physical-channel colors", fontsize=18, fontweight="bold")
    for ax, (title, channels) in zip(axes, rows):
        ax.set(xlim=(0, 6), ylim=(0, 1.6), title=title)
        ax.axis("off")
        for i, channel in enumerate(channels):
            x = i * 6 / len(channels)
            width = 6 / len(channels) - 0.12
            color = channel_color(channel)
            ax.add_patch(Rectangle((x, 0.45), width, 0.65, facecolor=color, edgecolor="#334155", linewidth=0.6))
            ax.text(x + width / 2, 1.22, channel, ha="center", va="center", fontsize=12, fontweight="bold")
            ax.text(x + width / 2, 0.22, color, ha="center", va="center", fontsize=10)
            log.logger.info("CHANNEL %s color=%s", channel, color)
    fig.text(0.5, 0.018, "Project display convention, not a 3GPP color requirement. "
             "This palette does not implement channel waveforms or PRACH-to-OFDM mapping.", ha="center", fontsize=10)
    output = Path(__file__).resolve().parent
    for suffix in ("png", "svg"):
        fig.savefig(output / f"NRGrid_channel_colors.{suffix}", dpi=150)
    plt.close(fig)
    (output / "NRGrid_channel_colors.json").write_text(
        json.dumps(dict(CHANNEL_COLORS), indent=2) + "\n", encoding="utf-8")
    log.logger.info("Saved channel palette PNG/SVG/JSON in %s", output)


if __name__ == "__main__":
    with ExampleLogger(__file__) as run:
        main(run)
