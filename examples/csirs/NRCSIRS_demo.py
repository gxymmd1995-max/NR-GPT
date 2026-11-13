"""Standalone CSI-RS OFDM/channel/LS example; figures display only."""

import numpy as np
from cell import NRCell
from csirs import NRCSIRS
from common import NROFDM
from channel import NRChannel


def run_case(plot=False, *, n_size_grid=52, n_rbs=24):
    cell = NRCell(n_size_grid=n_size_grid, subcarrier_spacing_khz=30, n_rx_antennas=2)
    resource = NRCSIRS(cell, row=1, density=3, n_rbs=n_rbs)
    gains = np.array([1 + 0.2j, 0.5 - 0.3j])
    wave = gains[:, None] * resource.waveform()
    wave, _ = NRChannel(cell).add_awgn(wave, snr_db=30, seed=42)
    grid = NROFDM(cell).demodulate(wave)
    result = resource.estimate(grid)
    if plot:
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 2, figsize=(11, 4), layout="constrained")
        axes[0].imshow(abs(grid[0]).T, origin="lower", aspect="auto")
        axes[0].set(
            xlabel="Slot symbol",
            ylabel="Carrier subcarrier",
            title="CSI-RS through AWGN",
        )
        axes[1].plot(gains.real, gains.imag, "o", label="True H")
        h = result["channel_estimates"]
        axes[1].plot(h.real, h.imag, "x", label="LS H")
        axes[1].set(xlabel="I", ylabel="Q", title="Flat channel estimates")
        axes[1].legend()
        plt.show()
    return dict(**result, cell=cell)


if __name__ == "__main__":
    print(run_case(True))
