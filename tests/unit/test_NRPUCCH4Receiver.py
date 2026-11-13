import numpy as np
import pytest
from cell import NRCell
from channel import NRChannel
from pucch import NRPUCCH4, NRPUCCH4Transmitter, NRPUCCH4Receiver


@pytest.mark.parametrize("sf,index", [(2, 0), (2, 1), (4, 0), (4, 1), (4, 2), (4, 3)])
@pytest.mark.parametrize("modulation", ["QPSK", "pi/2-BPSK"])
@pytest.mark.parametrize("extended", [False, True])
def test_noisy_time_chain(sf, index, modulation, extended):
    cell = NRCell(
        n_size_grid=6,
        n_rx_antennas=2,
        cyclic_prefix="extended" if extended else "normal",
        subcarrier_spacing_khz=60 if extended else 30,
    )
    r = NRPUCCH4(
        cell,
        prb=1,
        n_symbols=12,
        second_hop_prb=4,
        additional_dmrs=True,
        modulation=modulation,
        spreading_factor=sf,
        occ_index=index,
    )
    bits = [1, 0, 1, 1, 0, 0, 1]
    wave = (
        NRPUCCH4Transmitter(r).transmit(bits)["waveform"]
        * np.array([0.7 + 0.4j, -0.3 + 0.6j])[:, None]
    )
    ch = NRChannel(cell)
    wave = ch.frequency_offset(ch.timing_advance(wave, -2), 731, 0.23)
    wave, _ = ch.add_awgn(wave, snr_db=15, seed=42)
    receiver = NRPUCCH4Receiver(r, len(bits))
    out = receiver.receive(
        wave,
        known_delay_samples=2,
        known_frequency_offset_hz=731,
        known_initial_phase_rad=0.23,
    )
    assert out["bits"] == bits
    assert receiver.receive(np.zeros_like(wave))["bits"] is None


def test_polar_and_odd_length_smallblock():
    cell = NRCell(n_size_grid=6)
    for r, a in [
        (NRPUCCH4(cell, spreading_factor=2), 32),
        (NRPUCCH4(cell, modulation="pi/2-BPSK", spreading_factor=4, occ_index=3), 12),
        (NRPUCCH4(cell, n_symbols=4, modulation="pi/2-BPSK", spreading_factor=4), 3),
    ]:
        bits = np.random.default_rng(a).integers(0, 2, a).tolist()
        wave = NRPUCCH4Transmitter(r).transmit(bits)["waveform"]
        out = NRPUCCH4Receiver(r, a).receive(wave)
        assert out["bits"] == bits and out["crc_ok"] is not False


def test_four_users_same_time_frequency_by_occ():
    cell = NRCell(n_size_grid=6, n_rx_antennas=2)
    resources = [
        NRPUCCH4(
            cell,
            prb=1,
            n_symbols=12,
            second_hop_prb=4,
            spreading_factor=4,
            occ_index=i,
            rnti=100 + i,
        )
        for i in range(4)
    ]
    bits = [np.random.default_rng(i).integers(0, 2, 7).tolist() for i in range(4)]
    gains = np.array(
        [[1, 0.5 + 0.3j, 0.6j, -0.4 + 0.2j], [0.3j, 0.6, 0.3 + 0.4j, 0.7j]]
    )
    mixed = sum(
        gains[:, i, None] * NRPUCCH4Transmitter(r).transmit(bits[i])["waveform"]
        for i, r in enumerate(resources)
    )
    received, _ = NRChannel(cell).add_awgn(mixed, snr_db=15, seed=42)
    for i, r in enumerate(resources):
        assert NRPUCCH4Receiver(r, 7).receive(received)["bits"] == bits[i]


def test_shared_plotter_and_invalid_inputs():
    import numpy as np
    import pytest
    from cell import NRCell
    from diagnostics import NRPlotConfig, NRStagePlotter
    from pucch import NRPUCCH4, NRPUCCH4Transmitter, NRPUCCH4Receiver

    cell = NRCell(n_size_grid=12)
    r = NRPUCCH4(cell)
    trace = NRStagePlotter(NRPlotConfig(enabled=False))
    bits = [0, 1, 0]
    sent = NRPUCCH4Transmitter(r).transmit(bits, plotter=trace)
    rx = NRPUCCH4Receiver(r, len(bits))
    out = rx.receive(sent["waveform"], plotter=trace)
    assert out["detected"]
    with pytest.raises(TypeError):
        NRPUCCH4Receiver(None, 3)
    with pytest.raises(ValueError):
        rx.receive([[np.nan]])
    with pytest.raises(ValueError, match="0.6"):
        NRPUCCH4Receiver(r, int(0.8 * r.coded_length))
