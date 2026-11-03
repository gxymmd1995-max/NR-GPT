import numpy as np
import pytest
from common.NRULSCHCode import NRULSCHCode


@pytest.mark.parametrize('a,rate',[(16,.5),(160,.5),(256,.5),(512,.8)])
@pytest.mark.parametrize('rv',range(4))
def test_crc_ldpc_rate_matching(a,rate,rv):
    codec=NRULSCHCode(a,rate,5000,2,rv)
    bits=np.random.default_rng(a).integers(0,2,a)
    out=codec.decode(20*(1-2*codec.encode(bits)))
    assert out['crc_ok'] and out['converged'] and out['bits']==bits.tolist()


def test_no_success_on_parity_only_nonconvergence():
    c=NRULSCHCode(512,.5,1104,2,1)
    bits=np.random.default_rng(42).integers(0,2,512)
    out=c.decode(20*(1-2*c.encode(bits)))
    assert not out['converged'] and not out['crc_ok']


@pytest.mark.parametrize('args',[(17,.5,1024),(4000,.2,12000),(100,.5,1001)])
def test_unsupported(args):
    with pytest.raises(ValueError):NRULSCHCode(*args)
