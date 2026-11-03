import numpy as np
import pytest
from common.NRSmallBlockCode import NRSmallBlockCode as Code


@pytest.mark.parametrize('k',range(3,12))
@pytest.mark.parametrize('e',[16,32,96])
def test_soft_decode(k,e):
    bits=np.random.default_rng(k+e).integers(0,2,k).tolist()
    word=Code.encode(bits,e)
    assert Code.decode((1-2*word).astype(float),k)==bits


@pytest.mark.parametrize('bits',[[True,0,1],[0,1],[0]*12,[0,2,1]])
def test_reject_unsupported(bits):
    with pytest.raises(ValueError):Code.encode(bits,32)


def test_invalid_llr():
    with pytest.raises(ValueError):Code.decode([float('nan')]*32,3)
