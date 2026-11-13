import numpy as np
import pytest
from cell import NRCell
from channel import NRChannel
from pucch import NRPUCCH3, NRPUCCH3Transmitter, NRPUCCH3Receiver


@pytest.mark.parametrize("modulation", ["QPSK", "pi/2-BPSK"])
@pytest.mark.parametrize("a", [7, 12, 19, 32, 100])
@pytest.mark.parametrize("extended", [False, True])
def test_channel_chain(modulation, a, extended):
    cell = NRCell(
        n_size_grid=24,
        n_rx_antennas=2,
        cyclic_prefix="extended" if extended else "normal",
        subcarrier_spacing_khz=60 if extended else 30,
    )
    r = NRPUCCH3(
        cell,
        prb=1,
        n_prbs=3,
        start_symbol=1,
        n_symbols=10,
        second_hop_prb=12,
        additional_dmrs=True,
        modulation=modulation,
    )
    bits = np.random.default_rng(a).integers(0, 2, a).tolist()
    wave = (
        NRPUCCH3Transmitter(r).transmit(bits)["waveform"]
        * np.array([0.7 + 0.4j, -0.3 + 0.6j])[:, None]
    )
    ch = NRChannel(cell)
    wave = ch.frequency_offset(ch.timing_advance(wave, -2), 731, 0.23)
    wave, _ = ch.add_awgn(wave, snr_db=15, seed=42)
    receiver = NRPUCCH3Receiver(r, a)
    result = receiver.receive(
        wave,
        known_delay_samples=2,
        known_frequency_offset_hz=731,
        known_initial_phase_rad=0.23,
    )
    assert result["bits"] == bits and result["crc_ok"] is not False
    assert receiver.receive(np.zeros_like(wave))["bits"] is None


def test_shared_plotter_and_invalid_inputs():
    import numpy as np
    import pytest
    from cell import NRCell
    from diagnostics import NRPlotConfig, NRStagePlotter
    from pucch import NRPUCCH3, NRPUCCH3Transmitter, NRPUCCH3Receiver

    cell = NRCell(n_size_grid=12)
    r = NRPUCCH3(cell)
    trace = NRStagePlotter(NRPlotConfig(enabled=False))
    bits = [0, 1, 0]
    sent = NRPUCCH3Transmitter(r).transmit(bits, plotter=trace)
    rx = NRPUCCH3Receiver(r, len(bits))
    out = rx.receive(sent["waveform"], plotter=trace)
    assert out["detected"]
    with pytest.raises(TypeError):
        NRPUCCH3Receiver(None, 3)
    with pytest.raises(ValueError):
        rx.receive([[np.nan]])
    with pytest.raises(ValueError, match="0.6"):
        NRPUCCH3Receiver(r, int(0.8 * r.coded_length))
