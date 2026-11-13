"""F1完整时域闭环，图只显示，不保存。"""

import numpy as np
from cell import NRCell
from channel import NRChannel
from pucch import NRPUCCH1, NRPUCCH1Transmitter, NRPUCCH1Receiver
from diagnostics import ExampleLogger, NRPlotConfig, NRStagePlotter


def main(log, plot_config=None):
    cell = NRCell(n_cell_id=17, n_size_grid=6, n_rx_antennas=2)
    resource = NRPUCCH1(
        cell,
        prb=1,
        start_symbol=1,
        n_symbols=12,
        initial_cyclic_shift=3,
        hopping_id=731,
        group_hopping="enable",
        second_hop_prb=4,
        time_domain_occ=1,
    )
    trace = NRStagePlotter(
        NRPlotConfig(enabled=True) if plot_config is None else plot_config
    )
    sent = NRPUCCH1Transmitter(resource).transmit([0, 1], plotter=trace)
    channel = NRChannel(cell)
    wave = sent["waveform"] * np.array([0.7 + 0.4j, -0.3 + 0.6j])[:, None]
    wave = channel.timing_advance(wave, -2)
    wave = channel.frequency_offset(wave, 731, 0.23)
    wave, noise = channel.add_awgn(wave, snr_db=15, seed=42)
    trace.record("channel.received", wave, title="F1 after delay, CFO and SNR noise")
    result = NRPUCCH1Receiver(resource, 2).receive(
        wave,
        known_frequency_offset_hz=731,
        known_initial_phase_rad=0.23,
        known_delay_samples=2,
        plotter=trace,
    )
    log.logger.info(
        "F1 sent=[0,1], received=%s, metric=%s", result["bits"], result["metric"]
    )
    trace.show()
    return result


if __name__ == "__main__":
    with ExampleLogger(__file__) as run:
        main(run)
    import matplotlib.pyplot as plt

    plt.show()
