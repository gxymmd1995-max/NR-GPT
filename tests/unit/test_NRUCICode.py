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


def test_validation_and_corrupted_reliability_table(monkeypatch):
    import json
    from pathlib import Path
    import numpy as np
    import pytest
    from common.NRUCICode import NRUCICode
    with pytest.raises(ValueError,match='even'):NRUCICode(360,1089)
    with pytest.raises(ValueError):NRUCICode.crc([0],24)
    c=NRUCICode(12,64)
    for bits in [[0],np.full(12,2),np.zeros(12,float)]:
        with pytest.raises(ValueError):c.encode(bits)
    for llr in [[0],np.full(64,np.nan)]:
        with pytest.raises(ValueError):c.decode(llr)
    original=Path.read_text
    def corrupt(path,*args,**kwargs):
        if path.name=='_coding_tables.json':return json.dumps({'reliability':[]})
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'read_text',corrupt)
    with pytest.raises(ValueError,match='insufficient Polar'):c.polar_configuration()
