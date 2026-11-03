import numpy as np
import pytest
from cell import NRCell
from pusch import NRPUSCH


@pytest.mark.parametrize('mod',['QPSK','16QAM','64QAM','256QAM'])
@pytest.mark.parametrize('groups',[1,2])
def test_geometry_modulation(mod,groups):
    r=NRPUSCH(NRCell(n_size_grid=12),n_prbs=4,n_symbols=12,modulation=mod,cdm_groups_without_data=groups)
    points,labels=r.constellation()
    np.testing.assert_allclose(np.mean(abs(points)**2),1,atol=1e-14)
    assert len(np.unique(points))==2**r.modulation_order
    assert len(r.indices(True))==24
    assert len(r.indices())==(12*12-6*groups)*4
    assert set(map(tuple,r.indices())).isdisjoint(map(tuple,r.indices(True)))
    np.testing.assert_allclose(abs(r.dmrs()),1,atol=1e-14)


@pytest.mark.parametrize('kw',[dict(n_prbs=999),dict(start_symbol=3,dmrs_type_a_position=2,n_symbols=4),dict(modulation='BPSK'),dict(cdm_groups_without_data=3)])
def test_invalid(kw):
    with pytest.raises(ValueError):NRPUSCH(NRCell(),**kw)
