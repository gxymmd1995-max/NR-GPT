"""F2 7bit UCI编码/时域信道/软译码；只显示图，不保存。"""

import numpy as np
from cell import NRCell
from channel import NRChannel
from diagnostics import ExampleLogger, NRStagePlotter, NRPlotConfig
from pucch import NRPUCCH2, NRPUCCH2Transmitter, NRPUCCH2Receiver


def main(log, plot_config=None):
    cell = NRCell(n_cell_id=17, n_size_grid=12, n_rx_antennas=2)
    r = NRPUCCH2(
        cell,
        prb=1,
        n_prbs=3,
        start_symbol=8,
        n_symbols=2,
        rnti=4321,
        data_scrambling_id=731,
        dmrs_scrambling_id=271,
        second_hop_prb=6,
    )
    trace = NRStagePlotter(
        NRPlotConfig(enabled=True) if plot_config is None else plot_config
    )
    bits = [1, 0, 1, 1, 0, 0, 1]
    tx = NRPUCCH2Transmitter(r).transmit(bits, plotter=trace)
    ch = NRChannel(cell)
    wave = tx["waveform"] * np.array([0.7 + 0.4j, -0.3 + 0.6j])[:, None]
    wave = ch.frequency_offset(ch.timing_advance(wave, -2), 731, 0.23)
    wave, _ = ch.add_awgn(wave, snr_db=15, seed=42)
    trace.record(
        "channel.received", wave, title="Delay=2 samples, CFO=731 Hz, SNR=15 dB"
    )
    result = NRPUCCH2Receiver(r, len(bits)).receive(
        wave,
        known_frequency_offset_hz=731,
        known_initial_phase_rad=0.23,
        known_delay_samples=2,
        plotter=trace,
    )
    log.logger.info(
        "F2 sent=%s received=%s metric=%.6f", bits, result["bits"], result["metric"]
    )
    trace.show()
    return result


if __name__ == "__main__":
    with ExampleLogger(__file__) as run:
        main(run)
    import matplotlib.pyplot as plt

    plt.show()
