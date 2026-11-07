import numpy as np
import pytest
from cell import NRCell
from channel import NRChannel
from pucch import NRPUCCH1,NRPUCCH1Transmitter,NRPUCCH1Receiver


@pytest.mark.parametrize('bits',[[0],[1],[0,0],[0,1],[1,0],[1,1]])
@pytest.mark.parametrize('extended',[False,True])
def test_actual_waveform_through_channel(bits,extended):
    cell=NRCell(n_size_grid=6,n_rx_antennas=2,cyclic_prefix='extended' if extended else 'normal',subcarrier_spacing_khz=60 if extended else 30)
    r=NRPUCCH1(cell,n_symbols=10,second_hop_prb=4,time_domain_occ=1)
    x=NRPUCCH1Transmitter(r).transmit(bits)['waveform']*np.array([.7+.4j,-.3+.6j])[:,None]
    ch=NRChannel(cell)
    x=ch.frequency_offset(ch.timing_advance(x,-2),731,.23)
    x,_=ch.add_awgn(x,snr_db=20,seed=7)
    rx=NRPUCCH1Receiver(r,len(bits))
    result=rx.receive(x,known_frequency_offset_hz=731,known_initial_phase_rad=.23,known_delay_samples=2)
    assert result['detected'] and result['bits']==bits
    assert not rx.receive(np.zeros_like(x))['detected']


def test_invalid_waveform():
    rx=NRPUCCH1Receiver(NRPUCCH1(NRCell()))
    with pytest.raises(ValueError):rx.receive([[float('nan')]])


def test_reject_missing_resource():
    import pytest
    from pucch import NRPUCCH1Receiver
    with pytest.raises(TypeError):NRPUCCH1Receiver(None)


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
