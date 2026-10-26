"""OFDM的CP、频率坐标、相位、窗口和噪声缩放；另有MATLAB全向量对照。"""

from dataclasses import replace

import numpy as np
import pytest

from cell import NRCell
from common import NROFDM


@pytest.mark.parametrize("scs,cp",[(15,"normal"),(30,"normal"),(60,"normal"),(120,"normal"),(240,"normal"),(60,"extended")])
@pytest.mark.parametrize("slot",[0,1])
def test_roundtrip_exact_cp_and_all_fft_windows(scs,cp,slot):
    cell=NRCell(n_size_grid=6,subcarrier_spacing_khz=scs,cyclic_prefix=cp,n_slot=slot)
    model=NROFDM(cell,3500000123)
    rng=np.random.default_rng(12)
    grid=rng.normal(size=(2,cell.symbols_per_slot,72))+1j*rng.normal(size=(2,cell.symbols_per_slot,72))
    wave=model.modulate(grid)
    assert wave.shape==(2,cell.samples_per_slot)
    position=0
    for cp_length in cell.slot_cp_lengths_samples:
        np.testing.assert_allclose(wave[:,position:position+cp_length],wave[:,position+cell.n_fft:position+cell.n_fft+cp_length],atol=1e-14)
        position+=cp_length+cell.n_fft
    for fraction in (0,.5,1):
        np.testing.assert_allclose(model.demodulate(wave,fraction),grid,atol=1e-12)


def test_dc_tone_ifft_amplitude_frequency_origin_and_start_grid():
    cell=NRCell(n_size_grid=1)
    grid=np.zeros((1,14,12),complex);grid[0,:,6]=1
    wave=NROFDM(cell).modulate(grid)
    np.testing.assert_allclose(wave,1/cell.n_fft,atol=1e-15)
    np.testing.assert_array_equal(NROFDM(replace(cell,n_start_grid=10,bwp_start=10)).modulate(grid),wave)
    # 首个载波子载波为FFT中-6 bin，不是FFT bin0，也不因CRB起点直接增加频移。
    grid[0,:,6]=0;grid[0,:,0]=1
    wave=NROFDM(cell).modulate(grid)
    cp=cell.slot_cp_lengths_samples[0]
    np.testing.assert_allclose(wave[0,cp:cp+128],np.exp(-2j*np.pi*6*np.arange(128)/128)/128,atol=1e-15)


@pytest.mark.parametrize("kwargs,error",[({"cell":None},TypeError),({"carrier_frequency_hz":True},TypeError),({"carrier_frequency_hz":-1},ValueError)])
def test_constructor(kwargs,error):
    with pytest.raises(error):NROFDM(**({"cell":NRCell()}|kwargs))


@pytest.mark.parametrize("fraction,error",[(-.1,ValueError),(1.1,ValueError),(float("nan"),ValueError),(True,TypeError)])
def test_demod_fraction(fraction,error):
    model=NROFDM(NRCell(n_size_grid=1))
    with pytest.raises(error):model.demodulate(np.zeros((1,model.cell.samples_per_slot)),fraction)


def test_demod_requires_explicit_slot_length_and_valid_branches():
    model=NROFDM(NRCell(n_size_grid=1))
    for wave in (np.ones(100),np.ones((0,100)),np.full((1,100),np.nan),np.ones((1,model.cell.samples_per_slot+1))):
        with pytest.raises(ValueError):model.demodulate(wave)
