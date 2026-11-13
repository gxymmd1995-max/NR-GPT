from dataclasses import replace
import numpy as np
import pytest
from cell import NRCell
from channel import NRChannel
from ssb import NRSSB, NRSSBTransmitter, NRSSBReceiver
from diagnostics import NRStagePlotter, NRPlotConfig


@pytest.mark.parametrize(
    "lmax,index,hf", [(4, 3, 0), (4, 2, 1), (8, 7, 1), (64, 63, 0)]
)
@pytest.mark.parametrize("nrb", [24, 273])
def test_unknown_pci_index_time_chain(lmax, index, hf, nrb):
    cell = NRCell(
        n_cell_id=1007,
        n_size_grid=nrb,
        n_rx_antennas=2,
        subcarrier_spacing_khz=120 if lmax == 64 else 30,
    )
    r = NRSSB(
        cell, start_subcarrier=24, l_max=lmax, ssb_index=index, half_frame=hf, k_ssb=23
    )
    mib = [0, 1] * 12
    sent = NRSSBTransmitter(r).transmit(mib, sfn_lsb=6)
    h = np.array([0.7 + 0.4j, -0.3 + 0.6j])
    w = h[:, None] * sent["waveform"]
    ch = NRChannel(cell)
    w = ch.frequency_offset(ch.timing_advance(w, -2), 731, 0.23)
    w, _ = ch.add_awgn(w, 25, seed=42)
    receiver = NRSSBReceiver(
        replace(r, cell=replace(cell, n_cell_id=0), ssb_index=0, half_frame=0)
    )
    out = receiver.receive(
        w,
        known_delay_samples=2,
        known_frequency_offset_hz=731,
        known_initial_phase_rad=0.23,
    )
    assert (
        out["cell_id"] == 1007
        and out["ssb_index"] == index
        and out["mib"] == mib
        and out["sfn_lsb"] == 6
        and out["crc_ok"]
    )
    np.testing.assert_allclose(
        out["channel_estimates"], np.tile(h[:, None], (1, 3)), atol=0.01
    )
    trace = NRStagePlotter(NRPlotConfig(enabled=True, channel="SSB"))
    zero = receiver.receive(np.zeros_like(w), plotter=trace)
    assert not zero["detected"] and zero["cell_id"] is None and not zero["crc_ok"]
    assert "rx.pss_metrics" in trace.stages


def test_invalid_resource_and_waveform():
    with pytest.raises(TypeError):
        NRSSBReceiver(None)
    r = NRSSB(NRCell())
    rx = NRSSBReceiver(r)
    with pytest.raises(ValueError):
        rx.receive([[0]])
    with pytest.raises(ValueError):
        rx.receive([[np.nan]])
