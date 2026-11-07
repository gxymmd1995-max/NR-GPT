import numpy as np
import pytest
from cell import NRCell
from pucch import NRPUCCH4


@pytest.mark.parametrize('sf',[2,4])
def test_occ_orthogonal_and_inverse(sf):
    cell=NRCell(n_size_grid=6)
    resources=[NRPUCCH4(cell,spreading_factor=sf,occ_index=i) for i in range(sf)]
    w=np.array([r.occ() for r in resources]);np.testing.assert_allclose(w@w.conj().T/12,np.eye(sf),atol=1e-14)
    values=np.random.default_rng(42).normal(size=(len(resources[0].data_symbols),12//sf))+1j
    for r in resources:np.testing.assert_allclose(r.despread(r.spread(values)),values,atol=1e-14)
    for other in resources[1:]:np.testing.assert_allclose(resources[0].despread(other.spread(values)),0,atol=1e-14)


@pytest.mark.parametrize('sf,index,m0',[(2,0,0),(2,1,6),(4,0,0),(4,1,6),(4,2,3),(4,3,9)])
def test_dmrs_shift(sf,index,m0):
    r=NRPUCCH4(NRCell(),spreading_factor=sf,occ_index=index)
    np.testing.assert_allclose((r.dmrs()/r.base_resource().dmrs()).reshape(-1,12),
        np.tile(np.exp(2j*np.pi*m0*np.arange(12)/12),(len(r.dmrs_symbols),1)),atol=1e-14)


@pytest.mark.parametrize('kw',[dict(spreading_factor=3),dict(occ_index=2),dict(spreading_factor=4,occ_index=4)])
def test_invalid(kw):
    with pytest.raises(ValueError):NRPUCCH4(NRCell(),**kw)


def test_r15_sf4_table_order():
    r=NRPUCCH4(NRCell(),spreading_factor=4,occ_index=1)
    np.testing.assert_array_equal(r.occ(),[1]*3+[-1j]*3+[-1]*3+[1j]*3)


def test_resource_validation_boundaries():
    import numpy as np
    import pytest
    from cell import NRCell
    from grid import NRGrid
    from pucch import NRPUCCH4
    r=NRPUCCH4(NRCell())
    with pytest.raises(ValueError):r.map_to_grid(None,[0]*r.coded_length)
    with pytest.raises(ValueError):r.spread([[np.nan]])
    with pytest.raises(ValueError):r.despread([[np.nan]])
    with pytest.raises(ValueError):r.generate([0])
