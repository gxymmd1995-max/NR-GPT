"""100 MHz FR1 / 30 kHz carrier, NRSRS real waveform channel test. Images display only."""

import numpy as np
from cell import NRCell
from channel import NRChannel
from diagnostics import NRPlotConfig, NRStagePlotter, ExampleLogger
from srs import NRSRS, NRSRSReceiver
from grid import NRGrid
from common import NROFDM


def run_case(plot_config=None):
    """Return metadata, resource, sent arrays, receive result and passed; None disables plots."""
    cell = NRCell(
        n_cell_id=17, n_size_grid=273, subcarrier_spacing_khz=30, n_rx_antennas=2
    )
    r = NRSRS(cell, c_srs=63)
    bits = None
    trace = NRStagePlotter(plot_config)
    grid = NRGrid(cell, 1)
    r.map_to_grid(grid)
    sent = dict(grid=grid, waveform=NROFDM(cell).modulate(grid.data, plotter=trace))
    channel = NRChannel(cell)
    wave = sent["waveform"] * np.array([0.7 + 0.4j, -0.3 + 0.6j])[:, None]
    wave = channel.frequency_offset(channel.timing_advance(wave, -2), 731, 0.23)
    wave, _ = channel.add_awgn(wave, snr_db=25, seed=42)
    trace.record(
        "channel.received",
        wave,
        title="100MHz carrier: 2 Rx, delay2 samples, CFO731Hz, SNR25dB",
    )
    receiver = NRSRSReceiver(cell)
    corrected = channel.timing_advance(channel.frequency_offset(wave, -731, -0.23), 2)
    grid_rx = NROFDM(cell).demodulate(corrected, plotter=trace)
    mask = ~np.any(sent["grid"].occupancy, axis=0)
    result = receiver.estimate(grid_rx, {"UE0": r}, noise_mask=mask)
    passed = bool(result["users"]["UE0"]["delay_samples"] == 0)
    trace.show()
    return dict(
        channel="NRSRS",
        bandwidth_hz=100000000,
        scs_khz=30,
        n_prbs=273,
        n_fft=cell.n_fft,
        sample_rate_hz=cell.sample_rate_hz,
        passed=passed,
        resource=r,
        sent=sent,
        result=result,
    )


if __name__ == "__main__":
    with ExampleLogger(__file__) as log:
        out = run_case(
            NRPlotConfig(enabled=True, channel="SRS" if "NRSRS" != "NRSRS" else "SRS")
        )
        log.logger.info(
            "%s 100MHz/30kHz passed=%s Fs=%s FFT=%s",
            out["channel"],
            out["passed"],
            out["sample_rate_hz"],
            out["n_fft"],
        )
    import matplotlib.pyplot as plt

    plt.show()
