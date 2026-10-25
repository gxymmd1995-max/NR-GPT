"""运行后生成同级网格 NPZ、摘要 JSON、PNG/SVG 和调用日志。

示例中的资源标签和值均为软件映射演示，不代表实际 PDCCH/PDSCH/DM-RS。
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
import numpy as np

from cell import NRCell
from diagnostics import ExampleLogger
from grid import NRGrid, encode_owners


def plot_grid(grid: NRGrid, output: Path) -> None:
    """按逻辑端口绘制占用标签，BWP 边界使用载波局部子载波坐标。"""
    codes, labels, colors = encode_owners(grid.owners)
    fig, axes = plt.subplots(1, grid.n_ports, figsize=(12, 5.5), squeeze=False, layout="constrained")
    fig.get_layout_engine().set(rect=(0, 0.16, 1, 0.84))
    fig.suptitle(f"NRGrid | {grid.shape} [port, symbol, subcarrier] | "
                 f"{grid.occupied_re_count}/{grid.total_re_count} occupied REs", fontsize=14)
    start = (grid.cell.bwp_start - grid.cell.n_start_grid) * 12
    for port, ax in enumerate(axes[0]):
        ax.imshow(codes[port].T, origin="lower", aspect="auto", interpolation="nearest",
                  cmap=ListedColormap(colors), vmin=-0.5, vmax=len(colors) - 0.5)
        for boundary in (start - 0.5, start + grid.cell.bwp_size * 12 - 0.5):
            ax.axhline(boundary, color="#0F172A", linestyle="--", linewidth=1)
        ax.set(title=f"Logical port {port}", xlabel="Symbol within slot", ylabel="Carrier-local subcarrier",
               xticks=range(grid.n_symbols), yticks=range(0, grid.n_subcarriers, 12))
    legend = [Patch(facecolor=color, label=label) for label, color in zip(labels, colors)]
    fig.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, 0.065), ncols=min(5, len(labels)))
    fig.text(0.5, 0.02, "TS 38.211 V15.2.0 4.4.1-5; dashed lines = active BWP. "
             "Tags and values are synthetic mapping examples, not physical-channel waveforms.", ha="center", fontsize=9)
    for suffix in ("png", "svg"):
        fig.savefig(output / f"NRGrid_overview.{suffix}", dpi=150)
    plt.close(fig)


def main(log: ExampleLogger) -> None:
    """演示预留、两端口映射、零值占用、冲突检查及导出。"""
    cell = NRCell(n_size_grid=6, n_start_grid=10, bwp_start=11, bwp_size=4, n_tx_antennas=4)
    grid = NRGrid(cell, n_ports=2)
    log.dump_state(cell, "cell")
    reserved = grid.bwp_indices(range(4), [0])
    stream_a = grid.bwp_indices([0, 1], range(2, 10), [0])
    stream_b = grid.bwp_indices([2, 3], range(4, 12), [1])
    grid.reserve(reserved, "RESERVED")
    grid.map(stream_a, 1 + 1j, "STREAM_A")
    grid.map(stream_b, 1 - 1j, "STREAM_B")
    # 显式载波坐标允许 BWP 外资源；具体信道的 BWP 限制由信道模块负责。
    grid.map([[0, 13, 0]], 0, "ZERO")
    try:
        grid.map(stream_a[:1], 7, "CONFLICT")
    except ValueError as error:
        log.logger.info("Expected collision rejected without modifying grid: %s", error)
    # 小型演示网格完整打印；完整数据另存 NPZ，避免 NumPy 默认省略大数组。
    with np.printoptions(threshold=np.inf, linewidth=200):
        log.dump_state(grid, "grid")
    output = Path(__file__).resolve().parent
    summary = grid.summary()
    (output / "NRGrid_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    np.savez_compressed(output / "NRGrid_data.npz", data=grid.data, owners=grid.owners,
                        reserved_indices=reserved, stream_a_indices=stream_a, stream_b_indices=stream_b)
    plot_grid(grid, output)
    log.logger.info("Grid summary: %s", summary)
    log.logger.info("Saved grid JSON/NPZ/PNG/SVG in %s", output)


if __name__ == "__main__":
    with ExampleLogger(__file__) as run:
        main(run)
