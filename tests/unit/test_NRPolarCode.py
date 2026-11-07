import numpy as np
import pytest
from common.NRPolarCode import NRPolarCode


@pytest.mark.parametrize('n',[32,64,128,256,512,1024])
@pytest.mark.parametrize('interleaving',[False,True])
def test_decode(n,interleaving):
    c=NRPolarCode(min(n//2,128),n,interleaving)
    b=np.random.default_rng(n).integers(0,2,c.n_bits)
    x=c.encode(b);llr=(1-2*x)*10.+np.random.default_rng(n).normal(0,.1,n)
    np.testing.assert_array_equal(c.decode(llr),b)


def test_invalid():
    with pytest.raises(ValueError):NRPolarCode(10,33)


def test_reject_invalid_transform_vectors():
    for bits in [[], [[0,1]], [0,1,0], [0,2]]:
        with pytest.raises(ValueError,match='power-of-two'):NRPolarCode.transform(bits)


def test_validation_boundaries():
    for args in [(0,32,False),(10,32,1),(165,256,True)]:
        with pytest.raises((ValueError,TypeError)):NRPolarCode(*args)
    c=NRPolarCode(10,32)
    for bits in [[0],np.full(10,2),np.zeros(10,float)]:
        with pytest.raises(ValueError):c.encode(bits)
    for llr in [[0],np.full(32,np.nan)]:
        with pytest.raises(ValueError):c.decode(llr)
