import pytest
from cell import NRCell
from pdcch import NRPDCCH,NRPDCCHTransmitter
from diagnostics import NRStagePlotter,NRPlotConfig

def test_waveform_and_plotting():
    r=NRPDCCH(NRCell());t=NRPDCCHTransmitter(r)
    o=t.transmit([0,1]*16)
    assert o['waveform'].shape==(1,r.cell.samples_per_slot)
    t.transmit([0,1]*16,plotter=NRStagePlotter(NRPlotConfig(enabled=True,channel='PDCCH')))
    with pytest.raises(TypeError):NRPDCCHTransmitter(None)
