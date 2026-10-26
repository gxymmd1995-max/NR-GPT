"""TA零填充、命令量化、连续CFO与复AWGN功率定义。"""

import numpy as np
import pytest

from cell import NRCell
from channel import NRChannel
from common import NROFDM


def test_ta_is_non_circular_positive_advance_and_returns_copy():
    model=NRChannel(NRCell());x=np.arange(6,dtype=complex)[None,:]
    np.testing.assert_array_equal(model.timing_advance(x,2),[[2,3,4,5,0,0]])
    np.testing.assert_array_equal(model.timing_advance(x,-2),[[0,0,0,1,2,3]])
    np.testing.assert_array_equal(model.timing_advance(x,6),0)
    np.testing.assert_array_equal(model.timing_advance(x,-6),0)
    y=model.timing_advance(x,0);y[:]=99
    np.testing.assert_array_equal(x,np.arange(6)[None,:])
    with pytest.raises(ValueError):model.timing_advance(x,7)
    with pytest.raises(TypeError):model.timing_advance(x,.5)


@pytest.mark.parametrize("scs",[15,30,60,120,240])
def test_ta_command_samples_and_tc(scs):
    cell=NRCell(n_size_grid=52,subcarrier_spacing_khz=scs);model=NRChannel(cell)
    assert model.ta_command_samples(31)==0
    assert model.ta_command_samples(32)==cell.n_fft//128
    assert model.ta_command_samples(32)*cell.tc_per_sample==1024//(scs//15)
    assert model.ta_command_samples(0)==-31*cell.n_fft//128
    assert model.ta_command_samples(3846,True)==3846*cell.n_fft//128
    with pytest.raises(ValueError):model.ta_command_samples(64)
    with pytest.raises(TypeError):model.ta_command_samples(1,1)


def test_cfo_continuous_blocks_inverse_and_magnitude():
    model=NRChannel(NRCell());x=np.ones((2,1000),complex)
    whole=model.frequency_offset(x,1234,.37,100)
    first=model.frequency_offset(x[:,:300],1234,.37,100)
    second=model.frequency_offset(x[:,300:],1234,.37,400)
    np.testing.assert_allclose(np.concatenate((first,second),axis=1),whole,atol=1e-15)
    np.testing.assert_allclose(model.frequency_offset(whole,-1234,-.37,100),x,atol=1e-15)
    np.testing.assert_allclose(abs(whole),1,atol=1e-15)
    with pytest.raises(ValueError):model.frequency_offset(x,model.cell.sample_rate_hz/2)
    with pytest.raises(ValueError):model.frequency_offset(x,0,start_sample=-1)
    assert model.frequency_offset(x[:,:0],0).shape==(2,0)


def test_awgn_seed_per_branch_variance_and_supplied_noise():
    model=NRChannel(NRCell());x=np.ones((2,50000),complex);x[1]*=2
    y,n=model.add_awgn(x,snr_db=10,seed=42)
    np.testing.assert_array_equal(y,x+n)
    np.testing.assert_allclose(np.mean(abs(n)**2,axis=1),[.1,.4],rtol=.02)
    np.testing.assert_array_equal(n,model.add_awgn(x,10,seed=42)[1])
    small=np.ones((2,10),complex);standard=np.full(small.shape,1+1j)
    result,noise=model.add_awgn(small,20,noise_standard=standard)
    np.testing.assert_allclose(noise,.1*standard,atol=1e-16)
    np.testing.assert_array_equal(result,small+noise)
    np.testing.assert_array_equal(model.add_awgn(small*0,20)[0],small*0)
    # 0 dB means equal expected signal/noise power; negative SNR is supported.
    np.testing.assert_allclose(model.add_awgn(small,0,noise_standard=small)[1],small)
    np.testing.assert_allclose(model.add_awgn(small,-20,noise_standard=small)[1],10*small)
    with pytest.raises(TypeError):model.add_awgn(small,noise_power=.1)


def test_time_noise_to_fft_re_noise_scaling():
    cell=NRCell(n_size_grid=24);model=NRChannel(cell)
    _,noise=model.add_awgn(np.ones((1,cell.samples_per_slot)),40,seed=7)
    grid=NROFDM(cell).demodulate(noise)
    np.testing.assert_allclose(np.mean(abs(grid)**2),cell.n_fft*1e-4,rtol=.08)


@pytest.mark.parametrize("snr,error",[(True,TypeError),([1,2],TypeError),(float("nan"),ValueError),(float("inf"),ValueError),(1e308,ValueError),(-1e308,ValueError)])
def test_snr_validation(snr,error):
    with pytest.raises(error):NRChannel(NRCell()).add_awgn(np.ones((2,10)),snr)


def test_empty_signal_cannot_define_snr():
    with pytest.raises(ValueError,match="contain samples"):
        NRChannel(NRCell()).add_awgn(np.empty((2,0)),20)


def test_other_input_validation():
    with pytest.raises(TypeError):NRChannel(None)
    model=NRChannel(NRCell());x=np.ones((1,10))
    with pytest.raises(ValueError):model.add_awgn(x,1,noise_standard=np.ones((2,10)))
    with pytest.raises(ValueError):model.add_awgn(x,1,seed=0,noise_standard=x)
    with pytest.raises(TypeError):model.add_awgn(x,1,seed=True)
    with pytest.raises(ValueError):model.frequency_offset(np.full((1,10),np.nan),0)
