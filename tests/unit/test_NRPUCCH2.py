import numpy as np
import pytest
from cell import NRCell
from pucch import NRPUCCH2


def test_geometry_and_dmrs():
    r=NRPUCCH2(NRCell(n_size_grid=12),n_prbs=3,n_symbols=2,second_hop_prb=6)
    assert r.indices().shape==(48,3) and r.indices(True).shape==(24,3)
    assert set(map(tuple,r.indices())).isdisjoint(map(tuple,r.indices(True)))
    np.testing.assert_allclose(abs(r.dmrs()),1,atol=1e-14)
    np.testing.assert_allclose(abs(r.generate([0]*96)),1,atol=1e-14)


@pytest.mark.parametrize('kw',[dict(n_prbs=17),dict(n_symbols=3),dict(n_symbols=1,second_hop_prb=0),dict(rnti=-1),dict(dmrs_scrambling_id=65536)])
def test_invalid(kw):
    with pytest.raises(ValueError):NRPUCCH2(NRCell(),**kw)
