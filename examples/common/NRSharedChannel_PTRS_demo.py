"""Compare PUSCH/PDSCH decoding with PT-RS phase correction enabled or disabled."""

import argparse

import numpy as np

from cell import NRCell
from common import NROFDM
from pdsch import NRPDSCH, NRPDSCHReceiver, NRPDSCHTransmitter
from pusch import NRPUSCH, NRPUSCHReceiver, NRPUSCHTransmitter


def run_case(direction):
    if direction == "ul":
        resource_cls, tx_cls, rx_cls = NRPUSCH, NRPUSCHTransmitter, NRPUSCHReceiver
    else:
        resource_cls, tx_cls, rx_cls = NRPDSCH, NRPDSCHTransmitter, NRPDSCHReceiver
    cell = NRCell(n_size_grid=24, n_rx_antennas=2)
    resource = resource_cls(cell, prb=2, n_prbs=8, ptrs_config=(1, 2, 0))
    bits = np.random.default_rng(42).integers(0, 2, 256).tolist()
    tx = tx_cls(resource).transmit(bits, beta=0.8)
    # Common phase per symbol, with a different complex flat gain on each Rx.
    phase = 0.46 * (np.arange(cell.symbols_per_slot) - resource.dmrs_symbols[0])
    rotated = tx["grid"].data * np.exp(1j * phase)[None, :, None]
    gains = np.array([0.8 + 0.4j, -0.3 + 0.6j])
    received = gains[:, None] * NROFDM(cell).modulate(rotated)
    rx = rx_cls(resource, len(bits))
    before = rx.receive(received, correct_ptrs=False)
    after = rx.receive(received)
    return dict(
        resource=resource,
        phase=phase,
        before=before,
        after=after,
        passed=after["crc_ok"] and after["bits"] == bits,
    )


def plot_result(direction, result):
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(12, 4), layout="constrained")
    fig.suptitle(f"{direction.upper()} shared channel · same received waveform")
    for axis, label in zip(axes[:2], ("before", "after")):
        rx = result[label]
        points = rx["equalized_symbols"]
        axis.scatter(points.real, points.imag, s=8, alpha=0.5)
        axis.set(
            title=f'{label.capitalize()} correction · CRC={rx["crc_ok"]}',
            xlabel="I",
            ylabel="Q",
            xlim=(-1.1, 1.1),
            ylim=(-1.1, 1.1),
            aspect="equal",
        )
    axes[2].plot(result["phase"], label="Injected CPE")
    axes[2].plot(result["after"]["ptrs_phase_rad"], "--", label="Estimated CPE")
    axes[2].set(xlabel="Slot symbol", ylabel="Phase relative to DM-RS (rad)")
    axes[2].legend()
    plt.show()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("direction", choices=("ul", "dl"))
    parser.add_argument("--no-plot", action="store_true")
    args = parser.parse_args()
    result = run_case(args.direction)
    r = result["resource"]
    print(
        f"PT-RS RE={len(r.ptrs.indices())}, G={r.coded_length}, "
        f'CRC before={result["before"]["crc_ok"]}, CRC after={result["after"]["crc_ok"]}'
    )
    if not args.no_plot:
        plot_result(args.direction, result)
    return int(not result["passed"])


if __name__ == "__main__":
    raise SystemExit(main())
