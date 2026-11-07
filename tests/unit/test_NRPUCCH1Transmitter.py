import pytest
from cell import NRCell
from pucch import NRPUCCH1,NRPUCCH1Transmitter


def test_waveform_shape():
    cell=NRCell(n_size_grid=6)
    assert NRPUCCH1Transmitter(NRPUCCH1(cell)).transmit([0])['waveform'].shape==(1,cell.samples_per_slot)
    with pytest.raises(TypeError):NRPUCCH1Transmitter(None)


def test_shared_plotter_and_invalid_inputs():
    import numpy as np
    import pytest
    from cell import NRCell
    from diagnostics import NRPlotConfig,NRStagePlotter
    from pucch import NRPUCCH1,NRPUCCH1Transmitter,NRPUCCH1Receiver
    cell=NRCell(n_size_grid=12)
    r=NRPUCCH1(cell)
    trace=NRStagePlotter(NRPlotConfig(enabled=False))
    bits=[0]
    sent=NRPUCCH1Transmitter(r).transmit(bits,plotter=trace)
    rx=NRPUCCH1Receiver(r)
    out=rx.receive(sent['waveform'],plotter=trace)
    assert out['detected']
