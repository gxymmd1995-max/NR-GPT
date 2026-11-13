import pytest
from cell import NRCell
from ssb import NRSSB, NRSSBTransmitter
from diagnostics import NRStagePlotter, NRPlotConfig


def test_slot_waveform_and_trace():
    r = NRSSB(NRCell(n_size_grid=24))
    t = NRSSBTransmitter(r)
    sent = t.transmit([0, 1] * 12)
    assert sent["waveform"].shape == (1, r.cell.samples_per_slot)
    trace = NRStagePlotter(NRPlotConfig(enabled=True, channel="SSB"))
    t.transmit([0, 1] * 12, plotter=trace)
    assert "tx.pss" in trace.stages and "tx.pbch" in trace.stages
    with pytest.raises(TypeError):
        NRSSBTransmitter(None)
