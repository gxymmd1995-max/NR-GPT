"""OFDM单时隙、逐符号相位和提前FFT窗口演示，产物均保存在本目录。"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from cell import NRCell
from common import NROFDM, NRPhaseRotation
from diagnostics import ExampleLogger


def main(log):
    """展示60kHz slot1精确CP与NR符号相位，验证CP中点FFT恢复同一网格。"""
    output = Path(__file__).resolve().parent
    cell = NRCell(n_size_grid=24, subcarrier_spacing_khz=60, n_slot=1)
    model = NROFDM(cell, 3500000123)
    phase = NRPhaseRotation(cell, model.carrier_frequency_hz)
    rng = np.random.default_rng(20261026)
    grid = np.exp(1j * np.pi / 2 * rng.integers(0, 4, size=(2, 14, 288)))
    wave = model.modulate(grid)
    recovered = model.demodulate(wave, 0.5)
    error = float(np.max(abs(recovered - grid)))
    log.dump_state(cell, "cell")
    log.dump_state(model, "ofdm")
    log.dump_state(phase, "phase")
    log.logger.info("Per-symbol phase radians=%s", phase.symbol_phases().tolist())
    log.logger.info(
        "slot length=%d samples / %.9f us; max error=%g",
        cell.samples_per_slot,
        cell.slot_duration_s * 1e6,
        error,
    )
    summary = {
        "cell": cell.to_dict(),
        "carrier_frequency_hz": model.carrier_frequency_hz,
        "cp_fraction": 0.5,
        "symbol_phases_rad": phase.symbol_phases().tolist(),
        "cp_samples": list(cell.slot_cp_lengths_samples),
        "phasors_real": phase.symbol_phasors().real.tolist(),
        "phasors_imag": phase.symbol_phasors().imag.tolist(),
        "slot_samples": cell.samples_per_slot,
        "slot_duration_us": cell.slot_duration_s * 1e6,
        "max_roundtrip_error": error,
        "ifft_scale": "1/Nfft",
        "fft_scale": "1",
        "windowing": 0,
    }
    (output / "NROFDM_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    np.savez_compressed(
        output / "NROFDM_data.npz",
        grid=grid,
        waveform=wave,
        recovered_grid=recovered,
        symbol_phasors=phase.symbol_phasors(),
    )
    fig, axes = plt.subplots(2, 2, figsize=(12, 7), layout="constrained")
    fig.suptitle("NR OFDM | 60 kHz, slot 1 | per-symbol phase and CP-aware FFT")
    axes[0, 0].plot(np.arange(1200), abs(wave[0, :1200]))
    axes[0, 0].set(
        title="Time samples including CP",
        xlabel="Sample from slot start",
        ylabel="Magnitude",
    )
    axes[0, 1].plot(range(14), np.angle(phase.symbol_phasors()), "o-")
    axes[0, 1].set(
        title="NR symbol phase compensation (wrapped)",
        xlabel="Slot symbol",
        ylabel="radians",
    )
    axes[1, 0].bar(range(14), cell.slot_cp_lengths_samples)
    axes[1, 0].set(
        title=f"Actual slot duration = {cell.slot_duration_s*1e6:.6f} us",
        xlabel="Slot symbol",
        ylabel="CP samples",
    )
    axes[1, 1].scatter(
        grid.real.ravel()[:1000],
        grid.imag.ravel()[:1000],
        s=60,
        facecolors="none",
        edgecolors="black",
        label="Input",
    )
    axes[1, 1].scatter(
        recovered.real.ravel()[:1000],
        recovered.imag.ravel()[:1000],
        s=10,
        label="CP fraction 0.5 + phase recovery",
    )
    axes[1, 1].set(
        title=f"Input rings / recovered dots\nRoundtrip max error {error:.2e}",
        xlabel="I",
        ylabel="Q",
        aspect="equal",
    )
    fig.supxlabel(
        "TS38.211 V15.2.0 5.3.1/5.4; Nfft=512; no windowing/resampling; f0=3500000123 Hz",
        fontsize=9,
    )
    for suffix in ("png", "svg"):
        fig.savefig(output / f"NROFDM_overview.{suffix}", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    with ExampleLogger(__file__) as run:
        main(run)
