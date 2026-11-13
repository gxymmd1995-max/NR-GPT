"""F3 32-bit Polar UCI -> DFT-s-OFDM -> delayed/noisy channel -> CRC checked decode."""

import numpy as np
from cell import NRCell
from channel import NRChannel
from diagnostics import ExampleLogger, NRPlotConfig, NRStagePlotter
from pucch import NRPUCCH3, NRPUCCH3Transmitter, NRPUCCH3Receiver


def main(log, plot_config=None):
    cell = NRCell(n_cell_id=17, n_size_grid=24, n_rx_antennas=2)
    r = NRPUCCH3(
        cell,
        prb=1,
        n_prbs=3,
        start_symbol=1,
        n_symbols=12,
        rnti=4321,
        data_scrambling_id=731,
        hopping_id=271,
        group_hopping="enable",
        second_hop_prb=12,
        additional_dmrs=True,
    )
    trace = NRStagePlotter(
        NRPlotConfig(enabled=True) if plot_config is None else plot_config
    )
    bits = np.random.default_rng(42).integers(0, 2, 32).tolist()
    sent = NRPUCCH3Transmitter(r).transmit(bits, plotter=trace)
    ch = NRChannel(cell)
    wave = sent["waveform"] * np.array([0.7 + 0.4j, -0.3 + 0.6j])[:, None]
    wave = ch.frequency_offset(ch.timing_advance(wave, -2), 731, 0.23)
    wave, _ = ch.add_awgn(wave, snr_db=15, seed=42)
    trace.record("channel.received", wave, title="F3: sample delay / CFO / SNR noise")
    result = NRPUCCH3Receiver(r, len(bits)).receive(
        wave,
        known_delay_samples=2,
        known_frequency_offset_hz=731,
        known_initial_phase_rad=0.23,
        plotter=trace,
    )
    log.logger.info(
        "F3 bits_match=%s CRC=%s metric=%.6f",
        result["bits"] == bits,
        result["crc_ok"],
        result["metric"],
    )
    trace.show()
    return result


if __name__ == "__main__":
    with ExampleLogger(__file__) as run:
        main(run)
    import matplotlib.pyplot as plt

    plt.show()
