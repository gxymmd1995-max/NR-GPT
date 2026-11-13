"""Compare the remaining NR channels and reference signals by changing one setting."""

import argparse

import numpy as np

from cell import NRCell
from channel import NRChannel
from common import NROFDM
from csirs import NRCSIRS
from grid import NRGrid
from pdcch import NRPDCCH, NRPDCCHReceiver, NRPDCCHTransmitter
from pdsch import NRPDSCH, NRPDSCHReceiver, NRPDSCHTransmitter
from ptrs import NRDownlinkPTRS, NRUplinkPTRS
from pusch import NRPUSCH, NRPUSCHReceiver, NRPUSCHTransmitter
from srs import NRSRS
from ssb import NRSSB, NRSSBReceiver, NRSSBTransmitter

SETTINGS = {
    "pdcch": (1, 2, 3),
    "pdsch": (4, 7, 14),
    "pusch": (4, 7, 14),
    "ssb": (17, 18),
    "srs": (1, 2, 4),
    "csirs": (3, 1, 0.5),
    "ul-ptrs": (1, 2, 4),
    "dl-ptrs": (1, 2, 4),
}


def mark(grid, indices, label):
    """Mark port-0 coordinates in a [symbol, carrier subcarrier] display map."""
    grid[indices[:, 1], indices[:, 2]] = label


def coded_case(group, length, cell, grid, snr_db):
    """Decode a fixed payload through the same sample-domain impairment per case."""
    if group == "pdcch":
        resource = NRPDCCH(
            cell,
            frequency_resources=(0, 1, 2, 3),
            duration=length,
            aggregation_level=4,
            dmrs_type_a_position=3,
        )
        tx, rx = NRPDCCHTransmitter, NRPDCCHReceiver
        title = f"CORESET {length} sym, AL4"
    else:
        resource_cls, tx, rx = {
            "pdsch": (NRPDSCH, NRPDSCHTransmitter, NRPDSCHReceiver),
            "pusch": (NRPUSCH, NRPUSCHTransmitter, NRPUSCHReceiver),
        }[group]
        resource = resource_cls(
            cell, prb=1, n_prbs=4, n_symbols=length, dmrs_additional_position=1
        )
        title = f"{length} sym, 4 RB, QPSK"
    bits = (
        np.random.default_rng(42)
        .integers(0, 2, 32 if group == "pdcch" else 64)
        .tolist()
    )
    sent = tx(resource).transmit(bits)
    mark(grid, resource.indices(), 1)
    mark(grid, resource.indices(dmrs=True), 2)
    channel = NRChannel(cell)
    delayed = channel.timing_advance(sent["waveform"], -2)
    shifted = channel.frequency_offset(delayed, 731)
    received, _ = channel.add_awgn(shifted, snr_db=snr_db, seed=42)
    result = rx(resource, len(bits)).receive(
        received,
        known_delay_samples=2,
        known_frequency_offset_hz=731,
    )
    detail = f'{len(sent["coded_bits"])} coded bits, CRC={result["crc_ok"]}'
    passed = result["crc_ok"] and result["bits"] == bits
    return title, sent["waveform"], detail, passed, result


def ssb_case(cell, grid):
    """Compare how PCI moves PBCH DM-RS while the four-symbol allocation stays fixed."""
    resource = NRSSB(cell, start_subcarrier=24)
    mib = [0, 1] * 12
    sent = NRSSBTransmitter(resource).transmit(mib)
    for label, kind in enumerate(("pbch", "dmrs", "pss", "sss"), start=1):
        mark(grid, resource.indices(kind), label)
    result = NRSSBReceiver(resource).receive(sent["waveform"])
    passed = (
        result["crc_ok"]
        and result["mib"] == mib
        and result["cell_id"] == cell.n_cell_id
    )
    return (
        f"PCI {cell.n_cell_id}",
        sent["waveform"],
        f'recovered PCI={result["cell_id"]}',
        passed,
    )


def reference_case(group, setting, cell, grid):
    """Map a reference signal and inspect it after an actual OFDM round trip."""
    tx_grid = NRGrid(cell, 1)
    ofdm = NROFDM(cell)
    gain = 0.7 + 0.2j
    if group == "srs":
        resource = NRSRS(
            cell,
            n_symbols=setting,
            start_position=setting - 1,
            repetition=setting,
            k_tc=2,
        )
        title = f"{setting} SRS sym, comb 2, same-frequency repeats"
    elif group == "csirs":
        resource = NRCSIRS(cell, row=1 if setting == 3 else 2, density=setting)
        title = f"Row {resource.row}, density {setting:g}"
    else:
        ptrs_cls, shared_cls = (
            (NRUplinkPTRS, NRPUSCH) if group == "ul-ptrs" else (NRDownlinkPTRS, NRPDSCH)
        )
        resource = ptrs_cls(
            shared_cls(cell, n_prbs=8), time_density=setting, frequency_density=2
        )
        title = f"PT-RS time density {setting}, 8 RB"
    resource.map_to_grid(tx_grid)
    indices = resource.indices()
    mark(grid, indices, 2)
    waveform = ofdm.modulate(tx_grid.data)
    if group in ("ul-ptrs", "dl-ptrs"):
        # Apply symbol CPE before modulation, with a known flat channel at the receiver.
        phase = 0.04 * np.arange(cell.symbols_per_slot)
        received = ofdm.demodulate(
            gain * ofdm.modulate(tx_grid.data * np.exp(1j * phase)[None, :, None])
        )
        result = resource.estimate_phase(received, [gain], interpolate=True)
        error = np.max(abs(result["phase_rad"] - phase[result["symbols"]]))
        detail = (
            f'PT-RS symbols={result["symbols"].tolist()}, phase error={error:.1e} rad'
        )
    else:
        received = ofdm.demodulate(gain * waveform)
        if group == "csirs":
            estimate = resource.estimate(received)["channel_estimates"]
        else:
            obs = received[tuple(indices.T)]
            estimate = np.vdot(resource.generate().ravel(), obs) / len(obs)
        error = np.max(abs(estimate - gain))
        detail = f"{len(indices)} reference RE, flat gain error={error:.1e}"
    return title, waveform, detail, error < 1e-10


def run_case(group, setting, *, snr_db=25):
    cell = NRCell(
        n_size_grid=32,
        subcarrier_spacing_khz=30,
        n_cell_id=setting if group == "ssb" else 17,
    )
    grid = np.zeros((cell.symbols_per_slot, cell.n_subcarriers), dtype=np.uint8)
    result = None
    if group in ("pdcch", "pdsch", "pusch"):
        title, wave, detail, passed, result = coded_case(
            group, setting, cell, grid, snr_db
        )
    elif group == "ssb":
        title, wave, detail, passed = ssb_case(cell, grid)
    else:
        title, wave, detail, passed = reference_case(group, setting, cell, grid)
    return dict(
        title=title,
        cell=cell,
        grid=grid,
        wave=wave[0],
        detail=detail,
        passed=passed,
        result=result,
    )


def describe_resources(group, grid):
    """Use the displayed mask to count occupied OFDM symbols and REs."""
    symbols = np.flatnonzero(np.any(grid, axis=1)).tolist()
    if group == "ssb":
        names = ("PBCH", "DM-RS", "PSS", "SSS")
    elif group in ("pdcch", "pdsch", "pusch"):
        names = ("Data", "DM-RS")
    else:
        return f"symbols={symbols}, reference RE={np.count_nonzero(grid)}"
    counts = ", ".join(
        f"{name} RE={np.count_nonzero(grid == label)}"
        for label, name in enumerate(names, 1)
    )
    return f"symbols={symbols}, {counts}"


def plot_cases(group, cases):
    import matplotlib.pyplot as plt
    from matplotlib.colors import BoundaryNorm, ListedColormap
    from matplotlib.patches import Patch

    colors = ["#eee", "#0072b2", "#e69f00", "#009e73", "#cc79a7"]
    names = [
        "Data / control",
        "DM-RS" if group in ("pdcch", "pdsch", "pusch", "ssb") else "Reference",
        "PSS",
        "SSS",
    ]
    fig, axes = plt.subplots(
        len(cases),
        2,
        squeeze=False,
        sharex="col",
        figsize=(12, 2.6 * len(cases)),
        layout="constrained",
    )
    fig.suptitle(group.upper())
    active = np.flatnonzero(np.any([case["grid"] for case in cases], axis=(0, 1)))
    lo, hi = active[0], active[-1] + 1
    used = np.unique([case["grid"] for case in cases])
    for (grid_ax, wave_ax), case in zip(axes, cases):
        grid, cell = case["grid"], case["cell"]
        occupied_symbols = np.flatnonzero(np.any(grid, axis=1))
        grid_ax.imshow(
            grid[:, lo:hi].T,
            aspect="auto",
            origin="lower",
            extent=(-0.5, grid.shape[0] - 0.5, lo - 0.5, hi - 0.5),
            cmap=ListedColormap(colors),
            norm=BoundaryNorm(np.arange(6) - 0.5, 5),
        )
        grid_ax.set(
            title=case["title"],
            ylabel="Carrier subcarrier",
            xticks=range(grid.shape[0]),
        )
        time = np.arange(len(case["wave"])) * (1e6 / cell.sample_rate_hz)
        edges_us = np.r_[0, np.cumsum(cell.slot_symbol_lengths_samples)] * (
            1e6 / cell.sample_rate_hz
        )
        wave_ax.plot(time, case["wave"].real, linewidth=0.65)
        for symbol in occupied_symbols:
            grid_ax.axvline(symbol - 0.5, color="0.35", linestyle=":", linewidth=0.55)
            wave_ax.axvspan(
                edges_us[symbol], edges_us[symbol + 1], color="#0072b2", alpha=0.08
            )
            wave_ax.axvline(
                edges_us[symbol], color="0.35", linestyle=":", linewidth=0.55
            )
        end = occupied_symbols[-1] + 1
        grid_ax.axvline(end - 0.5, color="0.35", linestyle=":", linewidth=0.55)
        wave_ax.axvline(edges_us[end], color="0.35", linestyle=":", linewidth=0.55)
        wave_ax.set_xlim(0, edges_us[-1])
        wave_ax.set_ylabel("Tx I")
    axes[0, 0].legend(
        handles=[Patch(color=colors[i], label=names[i - 1]) for i in used if i],
        fontsize=8,
    )
    axes[-1, 0].set_xlabel("Slot OFDM symbol")
    axes[-1, 1].set_xlabel("Time from slot start (µs)")


def pdsch_snr_cases():
    """A fixed PDSCH allocation and seed, changing only sample-domain SNR."""
    return [(snr_db, run_case("pdsch", 7, snr_db=snr_db)) for snr_db in (25, -20)]


def plot_snr_cases(cases):
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(
        1,
        len(cases),
        squeeze=False,
        sharex=True,
        sharey=True,
        figsize=(10, 4.8),
        layout="constrained",
    )
    fig.suptitle("PDSCH equalized QPSK · same TB, allocation and noise seed")
    for axis, (snr_db, case) in zip(axes[0], cases):
        result = case["result"]
        points = result["equalized_symbols"]
        axis.scatter(points.real, points.imag, s=11, alpha=0.6, label="Equalized data")
        ideal = np.array([1 + 1j, 1 - 1j, -1 + 1j, -1 - 1j]) / np.sqrt(2)
        axis.scatter(
            ideal.real, ideal.imag, marker="x", color="black", label="Ideal QPSK"
        )
        axis.set(
            title=f'{snr_db:g} dB sample SNR · CRC={result["crc_ok"]}',
            xlabel="I",
            ylabel="Q",
        )
        axis.set_aspect("equal", adjustable="box")
        axis.grid(alpha=0.25)
    axes[0, 0].legend()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "group", choices=[*SETTINGS, "pdsch-snr", "all"], nargs="?", default="all"
    )
    parser.add_argument("--no-plot", action="store_true")
    args = parser.parse_args()
    if args.group == "pdsch-snr":
        cases = pdsch_snr_cases()
        for snr_db, case in cases:
            print(
                f'PDSCH SNR={snr_db:g} dB: {case["detail"]}, bits match={case["passed"]}'
            )
        if not args.no_plot:
            import matplotlib.pyplot as plt

            plot_snr_cases(cases)
            plt.show()
        return int(not cases[0][1]["passed"])
    passed = total = 0
    for group in SETTINGS if args.group == "all" else (args.group,):
        cases = [run_case(group, value) for value in SETTINGS[group]]
        for case in cases:
            print(
                f'{group.upper():8} {case["title"]:44} {case["detail"]}'
                f' | {describe_resources(group, case["grid"])}'
            )
            passed += bool(case["passed"])
            total += 1
        if not args.no_plot:
            plot_cases(group, cases)
    print(f"{passed}/{total} cases passed")
    if not args.no_plot:
        import matplotlib.pyplot as plt

        plt.show()
    return int(passed != total)


if __name__ == "__main__":
    raise SystemExit(main())
