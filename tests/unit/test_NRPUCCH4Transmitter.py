import pytest
from cell import NRCell
from pucch import NRPUCCH4,NRPUCCH4Transmitter


def test_time_waveform_and_rate():
    r=NRPUCCH4(NRCell(n_size_grid=6),spreading_factor=4,occ_index=3)
    sent=NRPUCCH4Transmitter(r).transmit([0,1,0,1,1,0,1])
    assert sent['waveform'].shape==(1,r.cell.samples_per_slot)
    with pytest.raises(ValueError):NRPUCCH4Transmitter(r).transmit([0]*100)


def test_shared_plotter_and_invalid_inputs():
    import numpy as np
    import pytest
    from cell import NRCell
    from diagnostics import NRPlotConfig,NRStagePlotter
    from pucch import NRPUCCH4,NRPUCCH4Transmitter,NRPUCCH4Receiver
    cell=NRCell(n_size_grid=12)
    r=NRPUCCH4(cell)
    trace=NRStagePlotter(NRPlotConfig(enabled=False))
    bits=[0,1,0]
    sent=NRPUCCH4Transmitter(r).transmit(bits,plotter=trace)
    rx=NRPUCCH4Receiver(r,len(bits))
    out=rx.receive(sent['waveform'],plotter=trace)
    assert out['detected']
    with pytest.raises(TypeError):NRPUCCH4Transmitter(None)
    with pytest.raises(ValueError,match='0.6'):NRPUCCH4Transmitter(r).transmit([0]*int(.8*r.coded_length))
