import numpy as np
import pytest
from cell import NRCell
from channel import NRChannel
from pusch import NRPUSCH,NRPUSCHTransmitter,NRPUSCHReceiver


@pytest.mark.parametrize('mod',['QPSK','16QAM','64QAM','256QAM'])
@pytest.mark.parametrize('extended',[False,True])
def test_time_channel(mod,extended):
    cell=NRCell(n_size_grid=12,n_rx_antennas=2,cyclic_prefix='extended' if extended else 'normal',subcarrier_spacing_khz=60 if extended else 30)
    r=NRPUSCH(cell,prb=1,n_prbs=4,start_symbol=1,n_symbols=10,modulation=mod)
    bits=np.random.default_rng(42).integers(0,2,256).tolist()
    wave=NRPUSCHTransmitter(r).transmit(bits)['waveform']*np.array([.7+.4j,-.3+.6j])[:,None]
    ch=NRChannel(cell);wave=ch.frequency_offset(ch.timing_advance(wave,-2),731,.23)
    wave,_=ch.add_awgn(wave,snr_db=30,seed=42)
    receiver=NRPUSCHReceiver(r,256)
    out=receiver.receive(wave,known_delay_samples=2,known_frequency_offset_hz=731,known_initial_phase_rad=.23)
    assert out['bits']==bits and out['crc_ok'] and out['converged'] and out['detected']
    zero=receiver.receive(np.zeros_like(wave))
    assert zero['bits'] is None and not zero['crc_ok'] and not zero['detected']
