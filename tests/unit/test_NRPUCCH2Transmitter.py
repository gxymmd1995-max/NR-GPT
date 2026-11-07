import pytest
from cell import NRCell
from pucch import NRPUCCH2,NRPUCCH2Transmitter


def test_transmit():
    r=NRPUCCH2(NRCell(n_size_grid=6))
    out=NRPUCCH2Transmitter(r).transmit([1,0,1])
    assert out['waveform'].shape==(1,r.cell.samples_per_slot)
    with pytest.raises(ValueError):NRPUCCH2Transmitter(r).transmit([0]*12)


def test_reject_insufficient_prbs():
    r=NRPUCCH2(NRCell(n_size_grid=6))
    with pytest.raises(ValueError,match='code rate'):NRPUCCH2Transmitter(r).transmit([0]*11)


def test_shared_plotter_and_invalid_inputs():
    import numpy as np
    import pytest
    from cell import NRCell
    from diagnostics import NRPlotConfig,NRStagePlotter
    from pucch import NRPUCCH2,NRPUCCH2Transmitter,NRPUCCH2Receiver
    cell=NRCell(n_size_grid=12)
    r=NRPUCCH2(cell)
    trace=NRStagePlotter(NRPlotConfig(enabled=False))
    bits=[0,1,0]
    sent=NRPUCCH2Transmitter(r).transmit(bits,plotter=trace)
    rx=NRPUCCH2Receiver(r,len(bits))
    out=rx.receive(sent['waveform'],plotter=trace)
    assert out['detected']
    with pytest.raises(TypeError):NRPUCCH2Transmitter(None)
