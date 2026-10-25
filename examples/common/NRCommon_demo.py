"""演示公共Gold序列和SRS u/v，所有产物均写入本目录。"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from cell import NRCell
from common import NRCommon
from diagnostics import ExampleLogger
from grid import channel_color


def main(log: ExampleLogger) -> None:
    """画128个Gold比特及一帧内每个SRS符号的组/序列跳变。"""
    output = Path(__file__).resolve().parent
    cell = NRCell(subcarrier_spacing_khz=30)
    seed = 42
    bits = NRCommon.gold_sequence(seed, 128)
    groups, sequences, symbol_numbers = [], [], []
    for slot in range(cell.slots_per_frame):
        args = (seed, slot, 8, 4, 144)
        groups.extend(NRCommon.srs_sequence_uv(*args, group_seq_hopping="groupHopping")["u"].tolist())
        sequences.extend(NRCommon.srs_sequence_uv(*args, group_seq_hopping="sequenceHopping")["v"].tolist())
        symbol_numbers.extend(range(slot*14+8, slot*14+12))
    log.dump_state(cell, "cell")
    log.dump_state(NRCommon(), "common")
    log.logger.info("c_init=%d; c(0:127)=%s", seed, bits.tolist())
    log.logger.info("groupHopping u=%s", groups)
    log.logger.info("sequenceHopping v=%s", sequences)
    result = {"c_init": seed, "gold_length": 128, "gold_offset": 0, "gold_bits": bits.tolist(),
              "cell": cell.to_dict(), "symbol_start": 8, "n_symbols": 4, "sequence_length": 144,
              "frame_symbol_indices": symbol_numbers, "group_hopping_u": groups,
              "sequence_hopping_v": sequences,
              "note": "groupHopping and sequenceHopping are two separate configurations, never enabled together."}
    (output/"NRCommon_sequences.json").write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    fig, axes = plt.subplots(3, 1, figsize=(12, 8), layout="constrained")
    fig.suptitle("NRCommon | Gold PRBS and SRS sequence selection | c_init = 42")
    color = channel_color("SRS")
    axes[0].step(np.arange(128), bits, where="mid", color="#0072B2")
    axes[0].set(title="Gold output c(n), after discarding 1600 bits", xlabel="Bit index n",
                ylabel="c(n)", yticks=[0, 1], ylim=(-0.15, 1.15))
    axes[1].scatter(symbol_numbers, groups, color=color, s=16)
    axes[1].set(title="Configuration A: groupHopping (v = 0)", xlabel="OFDM symbol index within frame",
                ylabel="Sequence group u", ylim=(-1, 30))
    axes[2].scatter(symbol_numbers, sequences, color=color, s=16)
    axes[2].set(title=f"Configuration B: sequenceHopping (u = {seed % 30}, M = 144 >= 72)",
                xlabel="OFDM symbol index within frame", ylabel="Sequence number v",
                yticks=[0, 1], ylim=(-0.15, 1.15))
    for ax in axes:
        ax.grid(alpha=0.15)
    fig.supxlabel("TS 38.211 V15.2.0 5.2.1 and 6.4.1.4.2; "
                  "SRS starts at symbol 8, spans 4 symbols per slot; u/v shown for separate hopping modes.", fontsize=9)
    for suffix in ("png", "svg"):
        fig.savefig(output/f"NRCommon_sequences.{suffix}", dpi=150)
    plt.close(fig)
    log.logger.info("Saved Gold/u/v JSON and PNG/SVG in %s", output)


if __name__ == "__main__":
    with ExampleLogger(__file__) as run:
        main(run)
