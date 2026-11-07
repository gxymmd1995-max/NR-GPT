import numpy as np
import pytest
from cell import NRCell
from pucch import NRPUCCH1


@pytest.mark.parametrize('length',range(4,15))
@pytest.mark.parametrize('hop',[None,4])
def test_geometry_and_unit_power(length,hop):
    r=NRPUCCH1(NRCell(n_size_grid=6),n_symbols=length,second_hop_prb=hop)
    assert r.indices().shape==(12*length,3)
    np.testing.assert_allclose(abs(r.generate([1,0])),1,atol=1e-14)


@pytest.mark.parametrize('kwargs',[dict(n_symbols=3),dict(time_domain_occ=7),dict(prb=99),dict(group_hopping='disable')])
def test_invalid_resource(kwargs):
    with pytest.raises(ValueError):NRPUCCH1(NRCell(),**kwargs)


def test_occ_walsh_and_bit_validation():
    r=NRPUCCH1(NRCell(),n_symbols=8,time_domain_occ=1)
    z=NRPUCCH1(NRCell(),n_symbols=8)
    np.testing.assert_allclose((r.reference()/z.reference())[1::2,0],[1,-1,1,-1],atol=1e-14)
    with pytest.raises(ValueError):r.generate([True])


def test_reject_missing_cell_and_mismatched_grid():
    from cell import NRCell
    from grid import NRGrid
    from pucch import NRPUCCH1
    import pytest
    with pytest.raises(TypeError):NRPUCCH1(None)
    resource=NRPUCCH1(NRCell())
    for grid in [None,NRGrid(NRCell(n_size_grid=6),1),NRGrid(resource.cell,2)]:
        with pytest.raises(ValueError,match='matching'):resource.map_to_grid(grid,[0])
