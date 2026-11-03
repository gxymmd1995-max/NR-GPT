import numpy as np
import pytest
from common.NRRMCode import NRRMCode


@pytest.mark.parametrize('r',[0,1,2,3])
def test_majority(r):
    c=NRRMCode(r,5);b=np.random.default_rng(r).integers(0,2,c.n_bits);x=c.encode(b)
    # RM minimum distance=2^(m-r), correct up to floor((d-1)/2) errors.
    llr=20*(1-2*x);llr[:(2**(5-r)-1)//2]*=-1
    np.testing.assert_array_equal(c.decode(llr),b)
