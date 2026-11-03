import numpy as np
import pytest
from common import NRUCICode


@pytest.mark.parametrize('a,e',[(3,16),(11,64),(12,48),(12,256),(19,512),(20,64),(100,240),(100,300),(360,1088),(1013,2304),(1706,4096)])
def test_complete_uci(a,e):
    c=NRUCICode(a,e);b=np.random.default_rng(a).integers(0,2,a)
    result=c.decode(20*(1-2*c.encode(b)))
    assert result['bits']==b.tolist() and result['crc_ok'] is not False


def test_crc_failure():
    result=NRUCICode(32,128).decode(np.random.default_rng(42).normal(size=128))
    assert result['crc_ok'] is False


@pytest.mark.parametrize('a,e',[(2,16),(1707,4096),(12,13)])
def test_invalid(a,e):
    with pytest.raises(ValueError):NRUCICode(a,e)
