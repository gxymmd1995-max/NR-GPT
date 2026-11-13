"""4-layer PDSCH through a mixed 4x4 time-domain channel, joint DMRS estimation/ZF."""

import numpy as np
from cell import NRCell
from channel import NRChannel
from diagnostics import ExampleLogger, NRPlotConfig, NRStagePlotter
from pdsch import NRPDSCH, NRPDSCHTransmitter, NRPDSCHReceiver


def main(log, plot_config=None):
    cell = NRCell(n_cell_id=17, n_size_grid=12, n_rx_antennas=4, n_tx_antennas=4)
    resource = NRPDSCH(
        cell,
        prb=1,
        n_prbs=2,
        start_symbol=1,
        n_symbols=12,
        n_layers=4,
        dmrs_configuration_type=2,
        dmrs_length=2,
        dmrs_additional_position=1,
        dmrs_ports=(1, 7, 4, 10),
        modulation="16QAM",
        rnti=4321,
        data_scrambling_id=731,
        dmrs_scrambling_id=271,
    )
    trace = NRStagePlotter(
        NRPlotConfig(enabled=True, channel="PDSCH")
        if plot_config is None
        else plot_config
    )
    bits = np.random.default_rng(42).integers(0, 2, 256).tolist()
    sent = NRPDSCHTransmitter(resource, n_ref=1440).transmit(bits, plotter=trace)
    channel = np.eye(4, dtype=complex) + (0.1 + 0.1j) * np.ones((4, 4))
    # One waveform per layer/identity-precoded Tx. Receiver only sees the summed Rx waveforms.
    received = channel @ sent["waveform"]
    propagation = NRChannel(cell)
    received = propagation.frequency_offset(
        propagation.timing_advance(received, -2), 731, 0.23
    )
    received, _ = propagation.add_awgn(received, snr_db=25, seed=42)
    trace.record(
        "channel.received",
        received,
        title="4x4 mixed MIMO, delay=2 samples, CFO731Hz, SNR25dB",
    )
    out = NRPDSCHReceiver(resource, len(bits), n_ref=1440).receive(
        received,
        known_delay_samples=2,
        known_frequency_offset_hz=731,
        known_initial_phase_rad=0.23,
        plotter=trace,
    )
    log.logger.info(
        "4-layer PDSCH bits_match=%s CRC=%s equalizer=%s condition=%s",
        out["bits"] == bits,
        out["crc_ok"],
        out["equalizer_ok"],
        out["condition_numbers"].tolist(),
    )
    trace.show()
    return out


if __name__ == "__main__":
    with ExampleLogger(__file__) as run:
        main(run)
    import matplotlib.pyplot as plt

    plt.show()
