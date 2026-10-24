"""绘制 NRCell 时频结构；原文依据见各坐标轴与类文档。"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from cell import NRCell
from diagnostics import ExampleLogger


def main(log: ExampleLogger) -> None:
    """生成 PNG/SVG，避免交互窗口；不将平均时隙示意当作精确 CP 时间轴。"""
    cell = NRCell(n_cell_id=42, n_start_grid=10, bwp_start=20, bwp_size=24)
    log.dump_state(cell, "cell")
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})
    fig, (time_ax, freq_ax) = plt.subplots(2, 1, figsize=(12, 8.4), layout="constrained")
    # 为图底的规范出处预留独立区域，避免与横轴标签重叠。
    fig.get_layout_engine().set(rect=(0, 0.055, 1, 0.945))
    fig.suptitle("NRCell | PCI 42 | SCS 30 kHz | normal CP", fontsize=18, fontweight="bold")

    for slot in range(cell.slots_per_frame):
        start_ms = slot * cell.nominal_slot_duration_s * 1000
        time_ax.add_patch(Rectangle((start_ms, 0), 0.5, 1, facecolor="#DBEAFE" if slot % 2 == 0 else "#93C5FD", edgecolor="white"))
        time_ax.text(start_ms + 0.25, 0.5, str(slot), ha="center", va="center")
    for subframe in range(10):
        time_ax.text(subframe + 0.5, 1.15, f"SF {subframe}", ha="center")
    time_ax.set(xlim=(0, 10), ylim=(-0.2, 1.5), yticks=[], xlabel="Nominal time (ms); numbers inside blocks = frame slot index",
                title="10 ms frame / 10 subframes / 20 slots / 14 symbols per slot")
    time_ax.set_xticks(range(11))
    time_ax.text(0, -0.95, "Source: TS 38.211 V15.2.0, 4.3.1 / Tables 4.3.2-1, 4.3.2-2. CP-level timing is not drawn.", transform=time_ax.transData, fontsize=9)

    freq_ax.add_patch(Rectangle((10, 0.8), 52, 0.6, facecolor="#DBEAFE", edgecolor="#2563EB"))
    freq_ax.add_patch(Rectangle((20, 0.88), 24, 0.44, facecolor="#10B981", edgecolor="#047857"))
    freq_ax.text(32, 1.1, "Active BWP: CRB [20, 44) = PRB [0, 24)", ha="center", va="center", fontsize=10)
    freq_ax.annotate("Point A\nCRB 0, subcarrier 0", xy=(0, 1.1), xytext=(0, 2.0), arrowprops={"arrowstyle": "->"}, ha="center")
    freq_ax.annotate("Carrier start: CRB 10\n+3.60 MHz from Point A", xy=(10, 0.8), xytext=(12, -0.1), arrowprops={"arrowstyle": "->"}, ha="center")
    freq_ax.annotate("Carrier end (exclusive): CRB 62\n624 subcarriers / nominal 18.72 MHz", xy=(62, 1.1), xytext=(47, 2.0), arrowprops={"arrowstyle": "->"}, ha="center")
    freq_ax.set(xlim=(-5, 68), ylim=(-0.65, 2.7), yticks=[], xlabel="Common resource block index (CRB); each RB has 12 subcarriers",
                title="Point A / carrier / BWP: distinct frequency coordinates")
    freq_ax.set_xticks([0, 10, 20, 44, 62])
    freq_ax.grid(axis="x", alpha=0.15)
    fig.text(0.5, 0.012, "Frequency source: TS 38.211 V15.2.0, 4.4.2 / 4.4.4.1-4 / 4.4.5. RF channel guard bands are not shown.", ha="center", fontsize=9)
    # 示例产物与脚本同级，移动工作目录不影响输出位置。
    output = Path(__file__).resolve().parent
    for suffix in ("png", "svg"):
        fig.savefig(output / f"NRCell_overview.{suffix}", dpi=160)
    plt.close(fig)
    log.logger.info("Saved overview PNG/SVG in %s", output)


if __name__ == "__main__":
    with ExampleLogger(__file__) as run:
        main(run)
