import numpy as np
import pytest
from common.NRBCHCode import NRBCHCode

@pytest.mark.parametrize('lmax,index',[(4,3),(8,7),(64,63)])
@pytest.mark.parametrize('hf',[0,1])
@pytest.mark.parametrize('sfn',range(16))
def test_bch_payload_and_crc(lmax,index,hf,sfn):
    c=NRBCHCode(1007,lmax,index,hf,23);b=[0,1]*12
    out=c.decode(20*(1-2*c.encode(b,sfn)))
    assert out['mib']==b and out['sfn_lsb']==sfn and out['half_frame']==hf and out['crc_ok']
    assert out['system_frame_number']==42*16+sfn
    assert out['extra_bits']==([1,1,1] if lmax==64 else [1,0,0])

@pytest.mark.parametrize('kw',[dict(cell_id=1008),dict(l_max=3),dict(ssb_index=8),dict(half_frame=2),dict(k_ssb=24)])
def test_invalid_configuration(kw):
    args=dict(cell_id=17);args.update(kw)
    with pytest.raises((ValueError,TypeError)):NRBCHCode(**args)

def test_invalid_vectors_and_crc_failure():
    c=NRBCHCode(17)
    for bits in [[0],[True]*24,[.0]*24,[2]*24]:
        with pytest.raises(ValueError):c.encode(bits)
    with pytest.raises(ValueError):c.encode([0]*24,sfn_lsb=16)
    with pytest.raises(ValueError):c.decode([np.nan]*864)
    out=c.decode(np.random.default_rng(42).normal(size=864))
    assert not out['crc_ok']
