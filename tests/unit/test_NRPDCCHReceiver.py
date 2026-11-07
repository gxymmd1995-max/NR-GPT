import numpy as np
import pytest
from cell import NRCell
from channel import NRChannel
from pdcch import NRPDCCH,NRPDCCHTransmitter,NRPDCCHReceiver
from diagnostics import NRStagePlotter,NRPlotConfig

@pytest.mark.parametrize('extended',[False,True])
def test_time_channel(extended):
    cell=NRCell(n_rx_antennas=2,subcarrier_spacing_khz=60 if extended else 30,cyclic_prefix='extended' if extended else 'normal')
    r=NRPDCCH(cell,aggregation_level=2)
    bits=[0,1]*16;wave=NRPDCCHTransmitter(r).transmit(bits)['waveform']*np.array([.7+.4j,-.3+.6j])[:,None]
    ch=NRChannel(cell);wave=ch.frequency_offset(ch.timing_advance(wave,-2),731,.23);wave,_=ch.add_awgn(wave,25,seed=42)
    rx=NRPDCCHReceiver(r,32)
    o=rx.receive(wave,known_frequency_offset_hz=731,known_initial_phase_rad=.23,known_delay_samples=2)
    assert o['bits']==bits and o['crc_ok']
    zero=rx.receive(np.zeros_like(wave),plotter=NRStagePlotter(NRPlotConfig(enabled=True,channel='PDCCH')))
    assert not zero['detected'] and zero['bits'] is None
    with pytest.raises(ValueError):rx.receive([[float('nan')]])

def test_invalid_resource():
    with pytest.raises(TypeError):NRPDCCHReceiver(None,32)
