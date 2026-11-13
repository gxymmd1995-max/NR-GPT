"""100 MHz FR1 / 30 kHz carrier, NRPRACH real waveform channel test. Images display only."""

import numpy as np
from cell import NRCell
from channel import NRChannel
from diagnostics import NRPlotConfig, NRStagePlotter, ExampleLogger
from prach import NRPRACH, NRPRACHTransmitter, NRPRACHReceiver


def run_case(plot_config=None):
    """Return metadata, resource, sent arrays, receive result and passed; None disables plots."""
    cell = NRCell(
        n_cell_id=17, n_size_grid=273, subcarrier_spacing_khz=30, n_rx_antennas=2
    )
    r = NRPRACH(
        cell,
        preamble_format="A1",
        subcarrier_spacing_khz=30,
        frequency_start=261,
        guard_samples=32,
    )
    bits = 7
    trace = NRStagePlotter(plot_config)
    sent = NRPRACHTransmitter(r).transmit(bits, plotter=trace)
    channel = NRChannel(cell)
    wave = sent["waveform"] * np.array([0.7 + 0.4j, -0.3 + 0.6j])[:, None]
    wave = channel.frequency_offset(channel.timing_advance(wave, -2), 731, 0.23)
    wave, _ = channel.add_awgn(wave, snr_db=25, seed=42)
    trace.record(
        "channel.received",
        wave,
        title="100MHz carrier: 2 Rx, delay2 samples, CFO731Hz, SNR25dB",
    )
    receiver = NRPRACHReceiver(r, max_delay_samples=8)
    result = receiver.receive(
        wave, known_frequency_offset_hz=731, known_initial_phase_rad=0.23, plotter=trace
    )
    passed = bool(
        result["best_preamble_index"] == 7
        and result["detections"][0]["delay_samples"] == 2
    )
    trace.show()
    return dict(
        channel="NRPRACH",
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
            NRPlotConfig(
                enabled=True, channel="PRACH" if "NRPRACH" != "NRSRS" else "SRS"
            )
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
