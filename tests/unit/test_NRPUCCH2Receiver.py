import numpy as np
import pytest
from cell import NRCell
from channel import NRChannel
from pucch import NRPUCCH2, NRPUCCH2Transmitter, NRPUCCH2Receiver


@pytest.mark.parametrize("k", range(3, 12))
@pytest.mark.parametrize("extended", [False, True])
def test_time_channel(k, extended):
    cell = NRCell(
        n_size_grid=12,
        n_rx_antennas=2,
        cyclic_prefix="extended" if extended else "normal",
        subcarrier_spacing_khz=60 if extended else 30,
    )
    r = NRPUCCH2(cell, n_prbs=3, start_symbol=8, n_symbols=2, second_hop_prb=6)
    bits = np.random.default_rng(k).integers(0, 2, k).tolist()
    x = (
        NRPUCCH2Transmitter(r).transmit(bits)["waveform"]
        * np.array([0.7 + 0.4j, -0.3 + 0.6j])[:, None]
    )
    ch = NRChannel(cell)
    x = ch.frequency_offset(ch.timing_advance(x, -2), 731, 0.23)
    x, _ = ch.add_awgn(x, snr_db=20, seed=42)
    rx = NRPUCCH2Receiver(r, k)
    assert (
        rx.receive(
            x,
            known_frequency_offset_hz=731,
            known_initial_phase_rad=0.23,
            known_delay_samples=2,
        )["bits"]
        == bits
    )
    assert rx.receive(np.zeros_like(x))["bits"] is None


def test_reject_insufficient_prbs():
    with pytest.raises(ValueError, match="code rate"):
        NRPUCCH2Receiver(NRPUCCH2(NRCell()), 11)


@pytest.mark.parametrize("a", [12, 19, 32, 100])
def test_polar_channel_chain(a):
    cell = NRCell(n_size_grid=24, n_rx_antennas=2)
    resource = NRPUCCH2(cell, n_prbs=8, start_symbol=8, n_symbols=2, second_hop_prb=12)
    bits = np.random.default_rng(a).integers(0, 2, a).tolist()
    wave = (
        NRPUCCH2Transmitter(resource).transmit(bits)["waveform"]
        * np.array([0.7 + 0.4j, -0.3 + 0.6j])[:, None]
    )
    channel = NRChannel(cell)
    wave = channel.frequency_offset(channel.timing_advance(wave, -2), 731, 0.23)
    wave, _ = channel.add_awgn(wave, snr_db=15, seed=42)
    out = NRPUCCH2Receiver(resource, a).receive(
        wave,
        known_delay_samples=2,
        known_frequency_offset_hz=731,
        known_initial_phase_rad=0.23,
    )
    assert out["bits"] == bits and out["crc_ok"] is True


def test_shared_plotter_and_invalid_inputs():
    import numpy as np
    import pytest
    from cell import NRCell
    from diagnostics import NRPlotConfig, NRStagePlotter
    from pucch import NRPUCCH2, NRPUCCH2Transmitter, NRPUCCH2Receiver

    cell = NRCell(n_size_grid=12)
    r = NRPUCCH2(cell)
    trace = NRStagePlotter(NRPlotConfig(enabled=False))
    bits = [0, 1, 0]
    sent = NRPUCCH2Transmitter(r).transmit(bits, plotter=trace)
    rx = NRPUCCH2Receiver(r, len(bits))
    out = rx.receive(sent["waveform"], plotter=trace)
    assert out["detected"]
    with pytest.raises(TypeError):
        NRPUCCH2Receiver(None, 3)
    with pytest.raises(ValueError):
        rx.receive([[np.nan]])
