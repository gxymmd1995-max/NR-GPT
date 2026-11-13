"""F4 single-user OCC / time-channel / decode demonstration, display only."""

import numpy as np
from cell import NRCell
from channel import NRChannel
from diagnostics import ExampleLogger, NRPlotConfig, NRStagePlotter
from pucch import NRPUCCH4, NRPUCCH4Transmitter, NRPUCCH4Receiver


def main(log, plot_config=None):
    cell = NRCell(n_cell_id=17, n_size_grid=6, n_rx_antennas=2)
    trace = NRStagePlotter(
        NRPlotConfig(enabled=True) if plot_config is None else plot_config
    )
    summaries = []
    for sf, index, a in [(2, 1, 32), (4, 3, 7)]:
        trace.prefix = f"F4.sf{sf}.occ{index}"
        r = NRPUCCH4(
            cell,
            prb=1,
            n_symbols=12,
            second_hop_prb=4,
            additional_dmrs=True,
            spreading_factor=sf,
            occ_index=index,
            rnti=4321,
            data_scrambling_id=731,
            hopping_id=271,
            group_hopping="enable",
        )
        bits = np.random.default_rng(a).integers(0, 2, a).tolist()
        sent = NRPUCCH4Transmitter(r).transmit(bits, plotter=trace)
        ch = NRChannel(cell)
        wave = sent["waveform"] * np.array([0.7 + 0.4j, -0.3 + 0.6j])[:, None]
        wave = ch.frequency_offset(ch.timing_advance(wave, -2), 731, 0.23)
        wave, _ = ch.add_awgn(wave, snr_db=15, seed=42)
        trace.record(
            "channel.received", wave, title="F4: 2-sample delay, CFO731Hz, SNR15dB"
        )
        result = NRPUCCH4Receiver(r, a).receive(
            wave,
            known_delay_samples=2,
            known_frequency_offset_hz=731,
            known_initial_phase_rad=0.23,
            plotter=trace,
        )
        log.logger.info(
            "F4 SF=%s OCC=%s bits_match=%s CRC=%s",
            sf,
            index,
            result["bits"] == bits,
            result["crc_ok"],
        )
        summaries.append(
            dict(sf=sf, occ=index, bits_match=result["bits"] == bits, **result)
        )
    trace.show()
    return summaries


if __name__ == "__main__":
    with ExampleLogger(__file__) as run:
        main(run)
    import matplotlib.pyplot as plt

    plt.show()
