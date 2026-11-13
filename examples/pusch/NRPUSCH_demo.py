"""Single-layer PUSCH transport block over a time-domain channel, display only."""

import numpy as np
from cell import NRCell
from channel import NRChannel
from diagnostics import ExampleLogger, NRPlotConfig, NRStagePlotter
from pusch import NRPUSCH, NRPUSCHTransmitter, NRPUSCHReceiver


def main(log, plot_config=None):
    cell = NRCell(n_cell_id=17, n_size_grid=12, n_rx_antennas=2)
    resource = NRPUSCH(
        cell,
        prb=1,
        n_prbs=4,
        start_symbol=1,
        n_symbols=12,
        modulation="16QAM",
        rnti=4321,
        data_scrambling_id=731,
        dmrs_scrambling_id=271,
    )
    trace = NRStagePlotter(
        NRPlotConfig(enabled=True, channel="PUSCH")
        if plot_config is None
        else plot_config
    )
    bits = np.random.default_rng(42).integers(0, 2, 256).tolist()
    sent = NRPUSCHTransmitter(resource).transmit(bits, plotter=trace)
    channel = NRChannel(cell)
    wave = sent["waveform"] * np.array([0.7 + 0.4j, -0.3 + 0.6j])[:, None]
    wave = channel.frequency_offset(channel.timing_advance(wave, -2), 731, 0.23)
    wave, _ = channel.add_awgn(wave, snr_db=25, seed=42)
    trace.record(
        "channel.received", wave, title="PUSCH: delay=2 samples, CFO731Hz, SNR25dB"
    )
    out = NRPUSCHReceiver(resource, len(bits)).receive(
        wave,
        known_delay_samples=2,
        known_frequency_offset_hz=731,
        known_initial_phase_rad=0.23,
        plotter=trace,
    )
    log.logger.info(
        "PUSCH bits_match=%s CRC=%s LDPC=%s iterations=%s",
        out["bits"] == bits,
        out["crc_ok"],
        out["converged"],
        out["iterations"],
    )
    trace.show()
    return out


if __name__ == "__main__":
    with ExampleLogger(__file__) as run:
        main(run)
    import matplotlib.pyplot as plt

    plt.show()
