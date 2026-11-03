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
