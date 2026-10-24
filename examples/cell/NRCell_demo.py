"""运行：python examples/cell/NRCell_demo.py。"""

import json
import csv
from pathlib import Path

from cell import NRCell
from diagnostics import ExampleLogger


def main(log: ExampleLogger) -> None:
    """展示非零载波/BWP 起点、派生参数及 SFN 回绕。"""
    cell = NRCell(n_cell_id=42, n_start_grid=10, bwp_start=20, bwp_size=24,
                  n_frame=1023, n_slot=19, duplex_mode="TDD", n_tx_antennas=4, n_rx_antennas=2)
    log.dump_state(cell, "cell")
    log.logger.info("PRB 0 -> CRB %s, first subcarrier offset=%s Hz", cell.prb_to_crb(0), cell.subcarrier_offset_hz(0))
    log.logger.info("Next slot: %s", cell.with_slot_offset().to_dict())
    log.logger.info("First symbol: %s", cell.symbol_timing(0))
    # 可复用的配置中间文件与示例脚本放在同一目录。
    output = Path(__file__).resolve().with_name("NRCell_config.json")
    output.write_text(json.dumps(cell.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log.logger.info("Saved config: %s", output)
    timing = {
        "config": cell.to_dict(), "tc_s": cell.tc_s, "ts_s": cell.ts_s,
        "kappa": cell.KAPPA, "n_fft": cell.n_fft, "sample_rate_hz": cell.sample_rate_hz,
        "sample_period_s": cell.sample_period_s, "tc_per_sample": cell.tc_per_sample,
        "subframes_per_frame": cell.subframes_per_frame,
        "slots_per_subframe": cell.slots_per_subframe, "symbols_per_slot": cell.symbols_per_slot,
        "samples_per_frame": cell.samples_per_frame, "samples_per_subframe": cell.samples_per_subframe,
        "slot_start_sample": cell.slot_start_sample, "samples_per_slot": cell.samples_per_slot,
        "slot_duration_s": cell.slot_duration_s, "useful_symbol_length_tc": cell.useful_symbol_length_tc,
        "cp_lengths_tc": cell.cp_lengths_tc, "symbol_lengths_tc": cell.symbol_lengths_tc,
        "cp_lengths_samples": cell.cp_lengths_samples, "symbol_lengths_samples": cell.symbol_lengths_samples,
        "symbol_start_samples": cell.symbol_start_samples,
        "current_slot_symbols": [cell.symbol_timing(i) for i in range(cell.symbols_per_slot)],
    }
    output.with_name("NRCell_timing.json").write_text(json.dumps(timing, indent=2) + "\n", encoding="utf-8")
    with output.with_name("NRCell_timing.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        rows = timing["current_slot_symbols"]
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    log.logger.info("Saved timing JSON/CSV in %s", output.parent)


if __name__ == "__main__":
    with ExampleLogger(__file__) as run:
        main(run)
