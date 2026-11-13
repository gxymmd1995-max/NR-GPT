"""Compare supported OFDM-symbol lengths of PUCCH formats 0–4."""

import argparse

import numpy as np

from cell import NRCell
from channel import NRChannel
from pucch import (
    NRPUCCH0,
    NRPUCCH0Receiver,
    NRPUCCH0Transmitter,
    NRPUCCH1,
    NRPUCCH1Receiver,
    NRPUCCH1Transmitter,
    NRPUCCH2,
    NRPUCCH2Receiver,
    NRPUCCH2Transmitter,
    NRPUCCH3,
    NRPUCCH3Receiver,
    NRPUCCH3Transmitter,
    NRPUCCH4,
    NRPUCCH4Receiver,
    NRPUCCH4Transmitter,
)

FORMATS = (
    (NRPUCCH0, NRPUCCH0Transmitter, NRPUCCH0Receiver),
    (NRPUCCH1, NRPUCCH1Transmitter, NRPUCCH1Receiver),
    (NRPUCCH2, NRPUCCH2Transmitter, NRPUCCH2Receiver),
    (NRPUCCH3, NRPUCCH3Transmitter, NRPUCCH3Receiver),
    (NRPUCCH4, NRPUCCH4Transmitter, NRPUCCH4Receiver),
)


def select_cases(symbols_per_slot, fmt=None, n_symbols=None, *, all_lengths=False):
    """Select representative or all lengths from TS 38.211 V15.2.0 Table 6.3.2.1-1."""
    cases = []
    for format_index in range(len(FORMATS)) if fmt is None else (fmt,):
        short = format_index in (0, 2)
        allowed = range(1, 3) if short else range(4, symbols_per_slot + 1)
        if n_symbols is not None:
            lengths = (n_symbols,) if n_symbols in allowed else ()
        elif short or all_lengths:
            lengths = allowed
        else:
            lengths = (4, 7, symbols_per_slot)
        cases.extend((format_index, length) for length in lengths)
    return cases


def run_case(fmt, n_symbols, cyclic_prefix="normal"):
    """Send fixed UCI, apply a sample delay, CFO and AWGN, and recover the UCI."""
    # Use 60 kHz for both CP modes to isolate the CP and slot-length changes.
    cell = NRCell(subcarrier_spacing_khz=60, cyclic_prefix=cyclic_prefix)
    resource_cls, tx_cls, rx_cls = FORMATS[fmt]
    start = cell.symbols_per_slot - n_symbols
    # Two RB for F2/F3. F0/F1/F4 use one RB as defined by their format.
    rb_config = {"n_prbs": 2} if fmt in (2, 3) else {}
    resource = resource_cls(
        cell, prb=1, start_symbol=start, n_symbols=n_symbols, **rb_config
    )
    bits = [1, 0] if fmt in (0, 1) else [1, 0, 1, 1, 0, 0, 1]
    sent = tx_cls(resource).transmit(bits)
    channel = NRChannel(cell)
    delay, cfo_hz = 2, 731
    received = channel.timing_advance(sent["waveform"], -delay)
    received = channel.frequency_offset(received, cfo_hz)
    received, _ = channel.add_awgn(received, snr_db=22, seed=42)
    result = rx_cls(resource, len(bits)).receive(
        received,
        known_delay_samples=delay,
        known_frequency_offset_hz=cfo_hz,
    )
    decoded = result["harq_ack"] if fmt == 0 else result["bits"]

    # Label the actual mapped REs: 0 = unused, 1 = UCI, 2 = DM-RS.
    occupancy = sent["grid"].occupancy[0].astype(np.uint8)
    if fmt == 1:
        # F1 DM-RS on even resource-relative symbols, including the first one.
        occupancy[start : start + n_symbols : 2] *= 2
    elif fmt >= 2:
        dmrs = resource.indices(dmrs=True)
        occupancy[dmrs[:, 1], dmrs[:, 2]] = 2
    sample_edges = np.r_[0, np.cumsum(cell.slot_symbol_lengths_samples)]
    return {
        "format": fmt,
        "resource": resource,
        "occupancy": occupancy,
        "waveform": sent["waveform"][0],
        "sample_edges": sample_edges,
        "bits": bits,
        "decoded": decoded,
        "passed": result["detected"] and np.array_equal(bits, decoded),
    }


def plot_results(cases):
    """Display resource maps and transmitted slot waveforms."""
    import matplotlib.pyplot as plt
    from matplotlib.colors import BoundaryNorm, ListedColormap
    from matplotlib.patches import Patch

    palette = ListedColormap(["#f0f0f0", "#0072b2", "#e69f00"])
    norm = BoundaryNorm([-0.5, 0.5, 1.5, 2.5], palette.N)
    for fmt in sorted({case["format"] for case in cases}):
        group = [case for case in cases if case["format"] == fmt]
        for offset in range(0, len(group), 6):
            page = group[offset : offset + 6]
            fig, axes = plt.subplots(
                len(page),
                2,
                squeeze=False,
                sharex="col",
                figsize=(12, 1.9 * len(page) + 1),
                layout="constrained",
            )
            fig.suptitle(
                f'PUCCH F{fmt} · {page[0]["resource"].cell.cyclic_prefix} CP · 60 kHz'
            )
            for (grid_ax, wave_ax), case in zip(axes, page):
                r = case["resource"]
                occupancy = case["occupancy"]
                slots = r.cell.symbols_per_slot
                occupied_subcarriers = np.flatnonzero(np.any(occupancy, axis=0))
                k0, k1 = occupied_subcarriers[0], occupied_subcarriers[-1] + 1
                grid_ax.imshow(
                    occupancy[:, k0:k1].T,
                    origin="lower",
                    aspect="auto",
                    extent=(-0.5, slots - 0.5, k0 - 0.5, k1 - 0.5),
                    cmap=palette,
                    norm=norm,
                )
                grid_ax.set_ylabel(f"{r.n_symbols} sym.\nSubcarrier")
                grid_ax.set_xticks(range(slots))
                us_per_sample = 1e6 / r.cell.sample_rate_hz
                time = np.arange(len(case["waveform"])) * us_per_sample
                edges = case["sample_edges"] * us_per_sample
                wave_ax.plot(time, case["waveform"].real, linewidth=0.65)
                wave_ax.axvspan(
                    edges[r.start_symbol], edges[-1], color="#0072b2", alpha=0.10
                )
                for boundary in edges[r.start_symbol :]:
                    wave_ax.axvline(
                        boundary, color="0.45", linestyle=":", linewidth=0.65
                    )
                wave_ax.set_ylabel("I amplitude")
            axes[0, 0].legend(
                handles=[
                    Patch(color=palette(1), label="UCI"),
                    Patch(color=palette(2), label="DM-RS"),
                ],
                loc="upper left",
                fontsize=8,
            )
            axes[-1, 0].set_xlabel("Slot OFDM symbol")
            axes[-1, 1].set_xlabel("Time from slot start (µs)")
    plt.show()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", type=int, choices=range(5), dest="fmt")
    parser.add_argument(
        "--symbols", type=int, help="Number of OFDM symbols in the allocation"
    )
    parser.add_argument("--cp", choices=("normal", "extended"), default="normal")
    parser.add_argument("--all-lengths", action="store_true")
    parser.add_argument("--no-plot", action="store_true")
    args = parser.parse_args()
    slot_symbols = NRCell(
        subcarrier_spacing_khz=60, cyclic_prefix=args.cp
    ).symbols_per_slot
    configs = select_cases(
        slot_symbols, args.fmt, args.symbols, all_lengths=args.all_lengths
    )
    if not configs:
        parser.error("No PUCCH format supports the selected length and cyclic prefix.")
    print("Format  Start  Symbols  Duration (us)  UCI RE  DM-RS RE  Decoded")
    cases = [run_case(fmt, length, args.cp) for fmt, length in configs]
    for case in cases:
        r = case["resource"]
        duration_samples = (
            case["sample_edges"][-1] - case["sample_edges"][r.start_symbol]
        )
        duration_us = duration_samples * 1e6 / r.cell.sample_rate_hz
        uci = np.count_nonzero(case["occupancy"] == 1)
        dmrs = np.count_nonzero(case["occupancy"] == 2)
        print(
            f'F{case["format"]:<5} {r.start_symbol:>5}  {r.n_symbols:>7}  {duration_us:>13.3f}'
            f'  {uci:>6}  {dmrs:>8}  {case["decoded"]}'
        )
    passed = sum(case["passed"] for case in cases)
    print(f"{passed}/{len(cases)} cases decoded the expected UCI")
    if not args.no_plot:
        plot_results(cases)
    return int(passed != len(cases))


if __name__ == "__main__":
    raise SystemExit(main())
