"""100 MHz FR1 / 30 kHz carrier, NRPUCCH3 real waveform channel test. Images display only."""

import numpy as np
from cell import NRCell
from channel import NRChannel
from diagnostics import NRPlotConfig, NRStagePlotter, ExampleLogger
from pucch import NRPUCCH3, NRPUCCH3Transmitter, NRPUCCH3Receiver


def run_case(plot_config=None):
    """Return metadata, resource, sent arrays, receive result and passed; None disables plots."""
    cell = NRCell(
        n_cell_id=17, n_size_grid=273, subcarrier_spacing_khz=30, n_rx_antennas=2
    )
    r = NRPUCCH3(cell, prb=261, n_prbs=12)
    bits = [0, 1] * 16
    trace = NRStagePlotter(plot_config)
    sent = NRPUCCH3Transmitter(r).transmit(bits, plotter=trace)
    channel = NRChannel(cell)
    wave = sent["waveform"] * np.array([0.7 + 0.4j, -0.3 + 0.6j])[:, None]
    wave = channel.frequency_offset(channel.timing_advance(wave, -2), 731, 0.23)
    wave, _ = channel.add_awgn(wave, snr_db=25, seed=42)
    trace.record(
        "channel.received",
        wave,
        title="100MHz carrier: 2 Rx, delay2 samples, CFO731Hz, SNR25dB",
    )
    receiver = NRPUCCH3Receiver(r, len(bits))
    result = receiver.receive(
        wave,
        known_frequency_offset_hz=731,
        known_initial_phase_rad=0.23,
        known_delay_samples=2,
        plotter=trace,
    )
    passed = bool(result["bits"] == bits and result["crc_ok"])
    trace.show()
    return dict(
        channel="NRPUCCH3",
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
                enabled=True, channel="PUCCH" if "NRPUCCH3" != "NRSRS" else "SRS"
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
