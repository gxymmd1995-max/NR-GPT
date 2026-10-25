"""真实 R15 SRS 生成及 NRGrid 频域位置演示；所有输出均保存在本目录。"""

import csv
from dataclasses import replace
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
from grid import NRGrid, channel_color
from srs import NRSRS


def plot_allocation(srs: NRSRS, grid: NRGrid, output: Path) -> None:
    """画四端口完整载波网格与首个 SRS 符号的两 RB 梳齿细节。"""
    color = channel_color("SRS")
    indices = srs.indices()
    low = 12*(srs.cell.bwp_start-srs.cell.n_start_grid)
    fig, axes = plt.subplots(2, srs.n_ports, figsize=(16, 8), squeeze=False, layout="constrained",
                             gridspec_kw={"height_ratios": [2, 1]})
    fig.get_layout_engine().set(rect=(0, 0.09, 1, 0.91))
    fig.suptitle(f"R15 SRS | slot {srs.cell.n_slot} | comb {srs.k_tc} | "
                 f"{srs.bandwidth_rb} RB per symbol | {srs.n_ports} logical ports", fontsize=15)
    for p in range(srs.n_ports):
        ax = axes[0, p]
        ax.imshow(grid.occupancy[p].T, origin="lower", aspect="auto", interpolation="nearest",
                  cmap=ListedColormap([channel_color("FREE"), color]), vmin=0, vmax=1)
        for boundary in (low-0.5, low+12*srs.cell.bwp_size-0.5):
            ax.axhline(boundary, color="#0F172A", linestyle="--", linewidth=1)
        ax.set(title=f"Local port {p} / SRS port {1000+p}", xlabel="OFDM symbol in slot",
               ylabel="Carrier-local subcarrier k", xticks=range(0, grid.n_symbols, 2),
               yticks=range(0, grid.n_subcarriers, 96))
        selected = indices[(indices[:, 0] == p) & (indices[:, 1] == srs.symbol_start), 2]
        start = int(selected[0]//12*12)
        carriers = np.arange(start, start+24)
        values = np.isin(carriers, selected)
        ax = axes[1, p]
        ax.vlines(carriers[values], 0, 1, color=color, linewidth=2)
        ax.scatter(carriers[values], np.ones(np.count_nonzero(values)), color=color, s=25)
        ax.scatter(carriers[~values], np.zeros(np.count_nonzero(~values)), color="#94A3B8", s=12)
        ax.set(title=f"Comb detail at symbol {srs.symbol_start}", xlabel="Carrier-local k (two RBs)",
               xlim=(start-1, start+24), ylim=(-0.15, 1.2), yticks=[0, 1], yticklabels=["free", "SRS"],
               xticks=range(start, start+25, 4))
        ax.grid(axis="x", alpha=0.15)
    fig.legend(handles=[Patch(facecolor=color, label="SRS"), Patch(facecolor=channel_color("FREE"), label="Free")],
               loc="lower center", bbox_to_anchor=(0.5, 0.035), ncols=2, frameon=False)
    fig.text(0.5, 0.015, "TS 38.211 V15.2.0 6.4.1.4; dashed = active BWP. "
             "k=12*(CRB-NStartGrid)+subcarrier; ports 1/3 use shifted comb for this cyclic shift.",
             ha="center", fontsize=9)
    for suffix in ("png", "svg"):
        fig.savefig(output / f"NRSRS_allocation.{suffix}", dpi=150)
    plt.close(fig)


def plot_hopping(srs: NRSRS, output: Path) -> np.ndarray:
    """按真实 indices 绘制连续八个时隙的端口0跳频；返回 [absolute_slot,p,l,k]。"""
    rows = []
    fig, ax = plt.subplots(figsize=(14, 5), layout="constrained")
    for offset in range(8):
        resource = replace(srs, cell=srs.cell.with_slot_offset(offset))
        grid = NRGrid(resource.cell, resource.n_ports)
        resource.map_to_grid(grid)
        # 从 NRGrid 提取实际占用，不用配置参数画虚构频率矩形。
        coordinates = np.argwhere(grid.occupancy)
        rows.append(np.column_stack((np.full(len(coordinates), resource.absolute_slot), coordinates)))
        p0 = coordinates[coordinates[:, 0] == 0]
        ax.scatter(offset*srs.cell.symbols_per_slot+p0[:, 1], p0[:, 2]/12,
                   s=7, marker="s", linewidths=0, color=channel_color("SRS"))
        ax.axvline(offset*srs.cell.symbols_per_slot-0.5, color="#CBD5E1", linewidth=0.8)
    low = srs.cell.bwp_start-srs.cell.n_start_grid
    ax.set(title="R15 SRS frequency hopping across eight slots | logical port 0",
           xlabel=f"Slot index (each group contains {srs.cell.symbols_per_slot} OFDM symbols)",
           ylabel="Carrier-local RB coordinate k/12",
           xticks=np.arange(8)*srs.cell.symbols_per_slot+srs.cell.symbols_per_slot/2-0.5,
           xticklabels=[str(srs.cell.with_slot_offset(i).n_slot) for i in range(8)],
           yticks=range(low, low+srs.cell.bwp_size+1, 4), ylim=(low-1, low+srs.cell.bwp_size+1))
    ax.grid(axis="y", alpha=0.2)
    fig.supxlabel(f"TS 38.211 V15.2.0 6.4.1.4.3 | CSRS={srs.c_srs}, BSRS={srs.b_srs}, "
                  f"BHop={srs.b_hop}, repetition={srs.repetition}; "
                  "brown points are actual NRGrid SRS REs.", fontsize=9)
    for suffix in ("png", "svg"):
        fig.savefig(output / f"NRSRS_hopping.{suffix}", dpi=150)
    plt.close(fig)
    return np.concatenate(rows, axis=0)


def main(log: ExampleLogger) -> None:
    """创建小区、SRS 和网格，记录全量快照，导出数值/坐标/频率及图片。"""
    output = Path(__file__).resolve().parent
    cell = NRCell(n_cell_id=42, n_size_grid=52, n_start_grid=10,
                  bwp_start=20, bwp_size=24, n_tx_antennas=4, n_rx_antennas=2)
    srs = NRSRS(cell, n_ports=4, n_symbols=4, start_position=5,
                c_srs=7, b_srs=1, b_hop=0, k_tc=4, comb_offset=1,
                cyclic_shift=7, frequency_shift=10, sequence_id=42,
                group_seq_hopping="groupHopping")
    grid = NRGrid(cell, n_ports=srs.n_ports)
    indices = srs.indices()
    raw = srs.generate()
    count = srs.map_to_grid(grid)
    with np.printoptions(threshold=np.inf, linewidth=200):
        log.dump_state(cell, "cell")
        log.dump_state(srs, "srs")
        log.dump_state(grid, "grid")
    plot_allocation(srs, grid, output)
    hopping_srs = replace(srs, repetition=4)  # 同一 slot 的4个符号保持同一频率，跨 slot 跳变。
    hopping = plot_hopping(hopping_srs, output)
    params = {name: value.tolist() for name, value in srs.sequence_parameters().items()}
    summary = {"input": srs.to_dict(), "hopping_view_input": hopping_srs.to_dict(),
               "matlab_srs_config": srs.to_matlab_config(),
               "grid": grid.summary(), "sequence_shape": raw.shape, "sequence_parameters": params,
               "sequence_length": srs.sequence_length, "mapped_re_count": count,
               "grid_energy_beta1": float(np.sum(np.abs(grid.data)**2)),
               "permission_note": "This example assumes triggered/activated, uplink-permitted transmission; no TDD/DCI scheduler."}
    (output / "NRSRS_summary.json").write_text(json.dumps(summary, indent=2)+"\n", encoding="utf-8")
    np.savez_compressed(output / "NRSRS_data.npz", indices=indices, raw_symbols=raw,
                        data=grid.data, owners=grid.owners, hopping_indices=hopping)
    with (output / "NRSRS_frequency_positions.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["local_port", "srs_port", "slot_symbol", "carrier_subcarrier", "crb",
                         "subcarrier_in_rb", "offset_from_carrier_center_hz", "offset_from_point_a_hz"])
        for p, l, k in indices:
            writer.writerow([p, 1000+p, l, k, cell.n_start_grid+k//12, k % 12,
                             (int(k)-cell.n_subcarriers//2)*cell.subcarrier_spacing_khz*1000,
                             cell.subcarrier_offset_hz(int(k))])
    log.logger.info("Mapped %d SRS REs; raw shape=%s; energy(beta=1)=%g", count, raw.shape, summary["grid_energy_beta1"])
    log.logger.info("Saved SRS vectors, frequency CSV, grid/hopping figures and log in %s", output)


if __name__ == "__main__":
    with ExampleLogger(__file__) as run:
        main(run)
