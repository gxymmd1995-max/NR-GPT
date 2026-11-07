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


@pytest.mark.parametrize('layers',[2,3,4])
@pytest.mark.parametrize('type,length',[(1,1),(1,2),(2,1),(2,2)])
@pytest.mark.parametrize('extended',[False,True])
def test_mixed_mimo_time_chain(layers,type,length,extended):
    cell=NRCell(n_size_grid=12,n_rx_antennas=4,cyclic_prefix='extended' if extended else 'normal',subcarrier_spacing_khz=60 if extended else 30)
    ports=((0,4,1,5) if type==1 else (0,6,4,10))[:layers] if length==2 else tuple(range(layers))
    r=NRPUSCH(cell,prb=1,n_prbs=2,start_symbol=1,n_symbols=10,n_layers=layers,
        dmrs_configuration_type=type,dmrs_length=length,dmrs_ports=ports,dmrs_additional_position=1,modulation='16QAM')
    bits=np.random.default_rng(42).integers(0,2,128).tolist()
    sent=NRPUSCHTransmitter(r).transmit(bits)
    h=np.eye(4,layers,dtype=complex)+(.1+.1j)*np.ones((4,layers))
    ch=NRChannel(cell);wave=h@sent['waveform']
    wave=ch.frequency_offset(ch.timing_advance(wave,-2),731,.23)
    wave,noise=ch.add_awgn(wave,snr_db=25,seed=42)
    receiver=NRPUSCHReceiver(r,len(bits))
    out=receiver.receive(wave,known_delay_samples=2,known_frequency_offset_hz=731,known_initial_phase_rad=.23)
    assert out['bits']==bits and out['crc_ok'] and out['equalizer_ok']
    assert out['layer_symbols'].shape[0]==layers
    assert out['channel_matrix'].shape==(4,layers,2)
    zero=receiver.receive(np.zeros_like(wave))
    assert not zero['detected'] and not zero['crc_ok']


def test_reject_rank_deficient_channel_and_underdetermined_receiver():
    cell=NRCell(n_size_grid=12,n_rx_antennas=2)
    r=NRPUSCH(cell,n_prbs=2,n_layers=2)
    tx=NRPUSCHTransmitter(r).transmit([0,1]*64)
    out=NRPUSCHReceiver(r,128).receive(np.ones((2,2))@tx['waveform'])
    assert out['detected'] and not out['equalizer_ok'] and not out['crc_ok'] and out['bits'] is None
    short=NRPUSCH(NRCell(n_size_grid=12,n_rx_antennas=1),n_layers=2)
    with pytest.raises(ValueError,match='n_rx'):NRPUSCHReceiver(short,128)


def test_invalid_resource_waveform_and_condition_limit():
    with pytest.raises(TypeError):NRPUSCHReceiver(None,128)
    r=NRPUSCH(NRCell(n_size_grid=12))
    with pytest.raises(ValueError):NRPUSCHReceiver(r,128,max_condition_number=.5)
    with pytest.raises(ValueError):NRPUSCHReceiver(r,128).receive([[float('nan')]])
