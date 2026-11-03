"""真实F0时域信号必须经过NRChannel，再给到接收机，不以原始网格旁路。"""

import numpy as np
import pytest

from cell import NRCell
from channel import NRChannel
from pucch import NRPUCCH0,NRPUCCH0Transmitter,NRPUCCH0Receiver


@pytest.mark.parametrize('cp,scs',[('normal',30),('extended',60)])
def test_waveform_ta_path_cfo_snr_then_receiver(cp,scs):
    cell=NRCell(n_size_grid=12,n_rx_antennas=2,cyclic_prefix=cp,subcarrier_spacing_khz=scs)
    r=NRPUCCH0(cell,prb=1,start_symbol=8,n_symbols=2,second_hop_prb=9,group_hopping='enable',hopping_id=1023)
    out=NRPUCCH0Transmitter(r,3500000123).transmit([1,0],1,.8)
    model=NRChannel(cell)
    advanced=model.timing_advance(out['waveform'],2)
    spatial=advanced*np.array([[1],[.6j]])
    delayed=model.timing_advance(spatial,-5)
    offset=model.frequency_offset(delayed,731,.23)
    received,noise=model.add_awgn(offset,snr_db=6,seed=7)
    result=NRPUCCH0Receiver(r,2,True,3500000123).receive(received,
        known_frequency_offset_hz=731,known_initial_phase_rad=.23,known_delay_samples=3)
    assert result['detected'] and result['harq_ack']==[1,0] and result['sr']==1
    assert result['m_cs']==10 and result['metric']>.9
    assert np.linalg.norm(noise)>0


@pytest.mark.parametrize('cp,scs',[('normal',30),('extended',60)])
@pytest.mark.parametrize('active',[('UE0','UE1','UE2'),('UE0','UE1'),('UE0',)])
def test_multiuser_shared_rb_is_separated_by_disjoint_cyclic_shift_sets(cp,scs,active):
    import importlib.util
    from pathlib import Path
    path=Path(__file__).resolve().parents[2]/'examples/pucch/NRPUCCH0_multiuser_demo.py'
    spec=importlib.util.spec_from_file_location('multiuser_example',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    summary,stored,results,_=module.run_case(active_users=active,cyclic_prefix=cp,subcarrier_spacing_khz=scs)
    assert summary['candidate_shift_sets']=={'UE0':[0,6],'UE1':[2,8],'UE2':[4,10]}
    assert summary['max_candidate_orthogonality_error']<2e-14
    np.testing.assert_allclose(stored['mixed_noiseless'],sum(stored[f'{uid}_channel_waveform'] for uid in results),atol=0)
    from common import NROFDM
    cell=NRCell(n_cell_id=17,n_size_grid=6,n_start_grid=10,bwp_start=11,bwp_size=4,n_rx_antennas=2,n_slot=3,
                cyclic_prefix=cp,subcarrier_spacing_khz=scs)
    channel=NRChannel(cell)
    corrected_noise=channel.timing_advance(channel.frequency_offset(stored['noise_waveform'],-731,-.23),3)
    noise_grid=NROFDM(cell,3500000123).demodulate(corrected_noise,.5)
    for uid,result in results.items():
        assert result['detected']==(uid in active)
        assert result['harq_ack']==(summary['true_harq_ack'][uid] if uid in active else None)
        # 每用户复相关应接近各自的beta*平坦复增益；没有把混合波形伪装成单用户输入。
        if uid in active:
            index=int(uid[-1]);g=np.array(summary['rx_gain_real'])[:,index]+1j*np.array(summary['rx_gain_imag'])[:,index]
            resource=NRPUCCH0(cell,prb=0,start_symbol=8,n_symbols=2,second_hop_prb=3,
                initial_cyclic_shift=summary['initial_cyclic_shifts'][index],hopping_id=731,group_hopping='enable')
            ix=resource.indices();reference=resource.generate(summary['true_harq_ack'][uid]).reshape(2,12)
            noise_projection=np.sum(noise_grid[:,ix[:,1],ix[:,2]].reshape(2,2,12)*reference.conj()[None,:,:],axis=2)/12
            np.testing.assert_allclose(result['correlation_symbols']-noise_projection,np.repeat(g[:,None],2,axis=1),atol=2e-14)
