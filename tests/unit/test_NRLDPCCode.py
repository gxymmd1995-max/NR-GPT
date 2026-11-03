import numpy as np
import pytest
from common.NRLDPCCode import NRLDPCCode


@pytest.mark.parametrize('bg',[1,2])
@pytest.mark.parametrize('z',[2,3,5,7,9,11,13,15,16])
def test_syndrome_and_decode(bg,z):
    c=NRLDPCCode(bg,z);b=np.random.default_rng(z).integers(0,2,c.n_bits)
    x=c.encode(b);full=np.concatenate([b[:2*z],x])
    assert all(np.sum(full[r])%2==0 for r in c.check_rows())
    out=c.decode(20*(1-2*x));assert out['converged']
    np.testing.assert_array_equal(out['bits'],b)


def test_invalid():
    with pytest.raises(ValueError):NRLDPCCode(3,2)
