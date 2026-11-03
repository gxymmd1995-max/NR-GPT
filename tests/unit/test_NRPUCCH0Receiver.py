"""未知复增益非相干合并、全部UCI候选、DTX以及同步输入约束。"""

from itertools import product

import numpy as np
import pytest

from cell import NRCell
from pucch import NRPUCCH0,NRPUCCH0Transmitter,NRPUCCH0Receiver


@pytest.mark.parametrize('n_ack,sr_enabled',[(0,True),(1,False),(1,True),(2,False),(2,True)])
@pytest.mark.parametrize('n_symbols',[1,2])
def test_all_payloads_unknown_rx_phase_and_dtx(n_ack,sr_enabled,n_symbols):
    cell=NRCell(n_size_grid=6,n_rx_antennas=2)
    r=NRPUCCH0(cell,start_symbol=10,n_symbols=n_symbols,second_hop_prb=4 if n_symbols==2 else None)
    receiver=NRPUCCH0Receiver(r,n_ack,sr_enabled)
    tx=NRPUCCH0Transmitter(r)
    for ack in product((0,1),repeat=n_ack):
        for sr in ((1,) if not n_ack else ((0,1) if sr_enabled else (None,))):
            wave=tx.transmit(ack,sr)['waveform']*np.array([[.3j],[-.9]])
            result=receiver.receive(wave)
            assert result['detected'] and result['harq_ack']==list(ack) and result['sr']==sr
            np.testing.assert_allclose(result['metric'],1,atol=1e-14)
            assert len(result['candidates'])==2**n_ack*(2 if sr_enabled and n_ack else 1)
    result=receiver.receive(np.zeros((2,cell.samples_per_slot)))
    assert result['status']=='dtx' and result['harq_ack'] is None
    assert result['sr']==(0 if n_ack==0 else None)


def test_noncoherent_combining_does_not_cancel_opposite_symbol_phases():
    cell=NRCell(n_size_grid=6)
    r=NRPUCCH0(cell,start_symbol=10,n_symbols=2)
    wave=NRPUCCH0Transmitter(r).transmit([1])['waveform']
    # 只对完整第二符号（CP和有效段）反相；跨符号相干和会抵消，但本接收机应保持指标1。
    position=0
    for symbol,cp in enumerate(cell.slot_cp_lengths_samples):
        if symbol==11:wave[:,position:position+cp+cell.n_fft]*=-1
        position+=cp+cell.n_fft
    result=NRPUCCH0Receiver(r).receive(wave)
    assert result['harq_ack']==[1]
    np.testing.assert_allclose(result['metric'],1)


def test_deterministic_noise_only_dtx_and_threshold_override():
    cell=NRCell(n_size_grid=6)
    r=NRPUCCH0(cell,n_symbols=2)
    rng=np.random.default_rng(8)
    noise=rng.normal(size=(1,cell.samples_per_slot))+1j*rng.normal(size=(1,cell.samples_per_slot))
    assert not NRPUCCH0Receiver(r,2,True).receive(noise)['detected']
    wave=NRPUCCH0Transmitter(r).transmit([1])['waveform']
    result=NRPUCCH0Receiver(r,detection_threshold=1).receive(wave)
    assert not result['detected']  # 指标严格大于门限才检测到，等于不算。


@pytest.mark.parametrize('kwargs,error',[
    ({'resource':None},TypeError),({'n_harq_ack_bits':3},ValueError),
    ({'n_harq_ack_bits':True},TypeError),({'sr_enabled':1},TypeError),
    ({'n_harq_ack_bits':0},ValueError),({'detection_threshold':-1},ValueError),
    ({'detection_threshold':float('nan')},ValueError),({'carrier_frequency_hz':-1},ValueError)])
def test_receiver_constructor_validation(kwargs,error):
    with pytest.raises(error):NRPUCCH0Receiver(**({'resource':NRPUCCH0(NRCell())}|kwargs))


def test_input_and_known_sync_validation():
    r=NRPUCCH0(NRCell(n_size_grid=6));receiver=NRPUCCH0Receiver(r)
    wave=NRPUCCH0Transmitter(r).transmit([1])['waveform']
    for invalid in (wave[:,:-1],np.repeat(wave,2,axis=0),wave*np.nan):
        with pytest.raises(ValueError):receiver.receive(invalid)
    with pytest.raises(TypeError):receiver.receive(wave,known_delay_samples=.5)
    with pytest.raises(ValueError):receiver.receive(wave,known_frequency_offset_hz=r.cell.sample_rate_hz)
    with pytest.raises(ValueError):receiver.receive(wave,cp_fraction=2)


def test_correlation_constellation_preserves_unknown_rx_gains_and_symbol_axes():
    cell=NRCell(n_size_grid=6,n_rx_antennas=2)
    resource=NRPUCCH0(cell,start_symbol=10,n_symbols=2)
    gains=np.array([[.7+.2j],[-.3+.6j]])
    sent=NRPUCCH0Transmitter(resource).transmit([1,0],1,beta=.8)
    result=NRPUCCH0Receiver(resource,2,True).receive(sent['waveform']*gains)
    assert result['correlation_symbols'].shape==(2,2)
    assert result['candidate_correlation_symbols'].shape==(8,2,2)
    np.testing.assert_allclose(result['correlation_symbols'],np.repeat(.8*gains,2,axis=1),atol=2e-15)
    assert result['harq_ack']==[1,0] and result['sr']==1
    # 信道相位保留在相关结果中；不会为伪造QPSK判决点而归一化/去掉复增益。
    best=result['candidates'].index(max(result['candidates'],key=lambda x:x['metric']))
    np.testing.assert_array_equal(result['correlation_symbols'],result['candidate_correlation_symbols'][best])


def test_cyclic_shift_group_checks_all_payload_hypotheses():
    from dataclasses import replace
    base=NRPUCCH0(NRCell(n_size_grid=6),n_symbols=2,start_symbol=8)
    group={f'UE{i}':NRPUCCH0Receiver(replace(base,initial_cyclic_shift=2*i)) for i in range(3)}
    assert NRPUCCH0Receiver.validate_cyclic_shift_group(group)=={'UE0':[0,6],'UE1':[2,8],'UE2':[4,10]}
    # m0不同仍可能相撞：m0=6的ACK0与m0=0的ACK1占用相同参考。
    group['UE1']=NRPUCCH0Receiver(replace(base,initial_cyclic_shift=6))
    with pytest.raises(ValueError,match='collision'):
        NRPUCCH0Receiver.validate_cyclic_shift_group(group)
    group={'A':NRPUCCH0Receiver(base,2),'B':NRPUCCH0Receiver(replace(base,initial_cyclic_shift=3))}
    with pytest.raises(ValueError,match='collision'):
        NRPUCCH0Receiver.validate_cyclic_shift_group(group)
    group={'A':NRPUCCH0Receiver(base),'SR':NRPUCCH0Receiver(replace(base,initial_cyclic_shift=2),0,True)}
    assert NRPUCCH0Receiver.validate_cyclic_shift_group(group)['SR']==[2]
    group={f'UE{i}':NRPUCCH0Receiver(replace(base,initial_cyclic_shift=i),2) for i in range(3)}
    assert NRPUCCH0Receiver.validate_cyclic_shift_group(group)=={'UE0':[0,3,6,9],'UE1':[1,4,7,10],'UE2':[2,5,8,11]}


@pytest.mark.parametrize('group',[{},[],{'A':None},{'':None},{' ':None},{1:None}])
def test_cyclic_shift_group_invalid_entries(group):
    with pytest.raises(ValueError):NRPUCCH0Receiver.validate_cyclic_shift_group(group)


@pytest.mark.parametrize('changes',[{'prb':1},{'hopping_id':2},{'start_symbol':9},
    {'n_symbols':1},{'second_hop_prb':3},{'group_hopping':'enable'}])
def test_cyclic_shift_group_requires_common_sequence_and_resources(changes):
    from dataclasses import replace
    base=NRPUCCH0(NRCell(n_size_grid=6),n_symbols=2,start_symbol=8)
    group={'A':NRPUCCH0Receiver(base),'B':NRPUCCH0Receiver(replace(base,**changes))}
    with pytest.raises(ValueError,match='share'):
        NRPUCCH0Receiver.validate_cyclic_shift_group(group)
