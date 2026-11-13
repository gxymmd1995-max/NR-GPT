"""Compare PRACH time-domain formats and RA/UL SCS pairs on explicit occasions."""

import argparse

import numpy as np

from cell import NRCell
from channel import NRChannel
from prach import NRPRACH, NRPRACHReceiver, NRPRACHTransmitter
from prach._tables import FORMATS, FREQUENCY


def select_cases(
    group="both", ra_scs=None, ul_scs=None, preamble_format=None, *, all_pairs=False
):
    """Return (format, RA SCS kHz, UL SCS kHz) configurations in display order."""
    if all_pairs or ra_scs is not None or ul_scs is not None:
        candidates = [
            (fmt, ra, ul)
            for fmt, (_, _, _, fixed_scs) in FORMATS.items()
            for ra, ul in FREQUENCY
            if (ra == fixed_scs if fixed_scs is not None else ra >= 15)
        ]
    else:
        # At 30 kHz UL SCS, compare every format at a fixed sample rate.
        candidates = [(fmt, params[3] or 15, 30) for fmt, params in FORMATS.items()]
        # With A1 held fixed, compare short-format numerologies as well.
        candidates.extend([("A1", 30, 30), ("A1", 60, 60), ("A1", 120, 120)])

    return [
        (fmt, ra, ul)
        for fmt, ra, ul in candidates
        if (group == "both" or group == ("long" if fmt.isdigit() else "short"))
        and (ra_scs is None or ra == ra_scs)
        and (ul_scs is None or ul == ul_scs)
        and (preamble_format is None or fmt == preamble_format)
    ]


def run_case(preamble_format, ra_scs, ul_scs):
    """Transmit preamble 7, add delay/CFO/AWGN, then search all 64 candidates."""
    cell = NRCell(n_size_grid=52, subcarrier_spacing_khz=ul_scs)
    resource = NRPRACH(
        cell,
        preamble_format=preamble_format,
        subcarrier_spacing_khz=ra_scs,
        zero_correlation_zone=8,
        guard_samples=32,
    )
    preamble, delay = 7, 3
    cfo_hz, initial_phase_rad = 731, 0.23
    sent = NRPRACHTransmitter(resource).transmit(preamble)
    channel = NRChannel(cell)
    received = channel.timing_advance(sent["waveform"], -delay)
    received = channel.frequency_offset(received, cfo_hz, initial_phase_rad)
    received, _ = channel.add_awgn(received, snr_db=25, seed=42)
    result = NRPRACHReceiver(
        resource, max_delay_samples=16, detection_threshold=0.55
    ).receive(
        received,
        known_frequency_offset_hz=cfo_hz,
        known_initial_phase_rad=initial_phase_rad,
    )
    actual = [(d["preamble_index"], d["delay_samples"]) for d in result["detections"]]
    return {
        "resource": resource,
        "waveform": sent["waveform"][0],
        "receiver": result,
        "expected": (preamble, delay),
        "passed": actual == [(preamble, delay)],
    }


def plot_results(results):
    """Display transmitted time waveforms and receiver correlation profiles."""
    import matplotlib.pyplot as plt

    rows_per_figure = 6
    families = [
        (
            label,
            [
                case
                for case in results
                if case["resource"].preamble_format.isdigit() == is_long
            ],
        )
        for label, is_long in [("Long", True), ("Short", False)]
    ]
    pages = [
        (label, cases[start : start + rows_per_figure])
        for label, cases in families
        for start in range(0, len(cases), rows_per_figure)
    ]
    for label, page in pages:
        fig, axes = plt.subplots(
            len(page),
            2,
            figsize=(12, 1.85 * len(page) + 1),
            squeeze=False,
            sharex="col",
            layout="constrained",
        )
        fig.suptitle(f"{label} PRACH waveforms and normalized preamble correlation")
        for (wave_ax, corr_ax), case in zip(axes, page):
            resource = case["resource"]
            cell = resource.cell
            sample_us = 1e6 / cell.sample_rate_hz
            cp_end = resource.cp_samples
            period_ends = cp_end + resource.n_fft * np.arange(
                1, resource.repetitions + 1
            )
            wave = case["waveform"]
            wave_ax.plot(np.arange(len(wave)) * sample_us, wave.real, linewidth=0.6)
            wave_ax.axvspan(
                0, cp_end * sample_us, color="tab:orange", alpha=0.25, label="CP"
            )
            wave_ax.axvspan(
                period_ends[-1] * sample_us,
                len(wave) * sample_us,
                color="0.7",
                alpha=0.35,
                label="Zero padding",
            )
            for boundary in [cp_end, *period_ends]:
                wave_ax.axvline(
                    boundary * sample_us, color="0.35", linestyle=":", linewidth=0.7
                )
            wave_ax.set_ylabel(f"{resource.preamble_format} | I")
            wave_ax.set_title(
                f"RA {resource.subcarrier_spacing_khz:g} / UL {cell.subcarrier_spacing_khz:g} kHz"
                f" · {resource.repetitions} period(s)",
                loc="left",
                fontsize=9,
            )
            rx = case["receiver"]
            preamble, delay = case["expected"]
            axis = rx["delay_axis_samples"]
            profile = rx["delay_profiles"][preamble]
            corr_ax.plot(
                axis, profile, "o-", markersize=3, label=f"Preamble {preamble}"
            )
            other = np.delete(rx["delay_profiles"], preamble, axis=0).max(axis=0)
            corr_ax.plot(axis, other, "--", label="Max other candidate")
            corr_ax.axvline(delay, color="0.35", linestyle=":", label="Injected delay")
            corr_ax.set_ylim(-0.04, 1.05)
            corr_ax.set_ylabel("Score")
        axes[0, 0].legend(loc="upper right", fontsize=8)
        axes[0, 1].legend(loc="upper right", fontsize=8)
        axes[-1, 0].set_xlabel("Time from PRACH occasion start (µs)")
        axes[-1, 1].set_xlabel("Delay (samples at this configuration’s sample rate)")
    plt.show()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--group", choices=("both", "long", "short"), default="both")
    parser.add_argument("--format", dest="preamble_format", choices=FORMATS)
    parser.add_argument("--ra-scs", type=float, help="PRACH subcarrier spacing in kHz")
    parser.add_argument(
        "--ul-scs", type=float, help="Uplink carrier subcarrier spacing in kHz"
    )
    parser.add_argument(
        "--all-pairs", action="store_true", help="Include all supported RA/UL SCS pairs"
    )
    parser.add_argument(
        "--no-plot", action="store_true", help="Run and print the comparison only"
    )
    args = parser.parse_args()
    configs = select_cases(
        args.group,
        args.ra_scs,
        args.ul_scs,
        args.preamble_format,
        all_pairs=args.all_pairs,
    )
    if not configs:
        parser.error(
            "No supported format/RA SCS/UL SCS combination matches these filters."
        )
    print(
        "Fmt   RA/UL kHz    Fs MS/s  FFT_RA  CP samples      CP us  Repeat  Active us   Detected (samples)"
    )
    results = []
    failed = 0
    for config in configs:
        case = run_case(*config)
        resource = case["resource"]
        fs = resource.cell.sample_rate_hz
        detected = [
            (d["preamble_index"], d["delay_samples"])
            for d in case["receiver"]["detections"]
        ]
        fmt, ra, ul = config
        print(
            f"{fmt:>3}  {ra:>5g}/{ul:<3g}  {fs / 1e6:>8.2f}  {resource.n_fft:>6}"
            f"  {resource.cp_samples:>10}  {resource.cp_samples / fs * 1e6:>9.3f}"
            f"  {resource.repetitions:>6}  {resource.active_samples / fs * 1e6:>9.3f}   {detected}"
        )
        failed += not case["passed"]
        if not args.no_plot:
            results.append(case)
    print(
        f"{len(configs) - failed}/{len(configs)} cases detected the expected preamble and delay"
    )
    if results:
        plot_results(results)
    return int(failed > 0)


if __name__ == "__main__":
    raise SystemExit(main())
