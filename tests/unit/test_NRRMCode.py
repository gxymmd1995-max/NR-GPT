import numpy as np
import pytest
from common.NRRMCode import NRRMCode


@pytest.mark.parametrize('r',[0,1,2,3])
def test_majority(r):
    c=NRRMCode(r,5);b=np.random.default_rng(r).integers(0,2,c.n_bits);x=c.encode(b)
    # RM minimum distance=2^(m-r), correct up to floor((d-1)/2) errors.
    llr=20*(1-2*x);llr[:(2**(5-r)-1)//2]*=-1
    np.testing.assert_array_equal(c.decode(llr),b)


def test_validation_boundaries():
    import numpy as np
    import pytest
    from common.NRRMCode import NRRMCode
    for kw in [dict(n_variables=0),dict(order=6)]:
        with pytest.raises(ValueError):NRRMCode(**kw)
    c=NRRMCode()
    for bits in [[0],np.full(c.n_bits,2),np.zeros(c.n_bits,float)]:
        with pytest.raises(ValueError):c.encode(bits)
    for llr in [[0],np.full(c.code_length,np.nan)]:
        with pytest.raises(ValueError):c.decode(llr)
