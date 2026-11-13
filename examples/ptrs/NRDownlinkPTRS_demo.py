"""Reference-only PT-RS waveform through known channel and symbol CPE."""

import numpy as np
from cell import NRCell
from grid import NRGrid
from common import NROFDM
from pdsch import NRPDSCH
from ptrs import NRDownlinkPTRS


def run_case(plot=False, *, n_size_grid=52):
    cell = NRCell(n_size_grid=n_size_grid, subcarrier_spacing_khz=30)
    # Place the allocation at the upper carrier edge; 17 RB exercises a partial
    # frequency-density interval without allocating the whole carrier to PT-RS.
    p = NRDownlinkPTRS(NRPDSCH(cell, prb=n_size_grid - 17, n_prbs=17), time_density=2)
    g = NRGrid(cell, 1)
    p.map_to_grid(g)
    # A toy payload RE in a symbol with no PT-RS shows interpolation in action.
    g.map([[0, 1, 12 * (n_size_grid - 17) + 5]], [1 + 1j], owner="PDSCH")
    # Known reference channel H=1; phase acts per OFDM symbol, not as CFO.
    symbols = p.indices()[:, 1]
    phases = 2.8 + 0.17 * np.clip(
        np.arange(cell.symbols_per_slot), symbols[0], symbols[-1]
    )
    wave = NROFDM(cell).modulate(g.data * np.exp(1j * phases)[None, :, None])
    received = NROFDM(cell).demodulate(wave)
    result = p.estimate_phase(received, np.ones(1), interpolate=True)
    assert np.allclose(result["corrected_grid"], g.data)
    if plot:
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 2, figsize=(11, 4), layout="constrained")
        axes[0].imshow(abs(g.data[0]).T, origin="lower", aspect="auto")
        axes[0].set(
            xlabel="Slot symbol",
            ylabel="Carrier subcarrier",
            title="NRDownlinkPTRS REs",
        )
        axes[1].plot(np.arange(14), phases, label="True CPE")
        aligned = result["correction_phase_rad"]
        aligned = aligned + 2 * np.pi * round((phases[0] - aligned[0]) / (2 * np.pi))
        axes[1].plot(
            result["correction_symbols"], aligned, "--", label="Interpolated CPE"
        )
        axes[1].set(xlabel="Slot symbol", ylabel="Phase / rad")
        axes[1].legend()
        plt.show()
    return dict(**result, cell=cell)


if __name__ == "__main__":
    r = run_case(True)
    print("symbols:", r["symbols"], "phase_rad:", r["phase_rad"])
