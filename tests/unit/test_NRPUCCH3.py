import pytest
import numpy as np
from cell import NRCell
from pucch import NRPUCCH3


@pytest.mark.parametrize('length',range(4,15))
@pytest.mark.parametrize('hop',[None,12])
@pytest.mark.parametrize('extra',[False,True])
def test_positions(length,hop,extra):
    r=NRPUCCH3(NRCell(n_size_grid=24),n_symbols=length,n_prbs=3,second_hop_prb=hop,additional_dmrs=extra)
    assert len(r.indices())+len(r.indices(True))==length*36
    assert set(map(tuple,r.indices())).isdisjoint(map(tuple,r.indices(True)))
    np.testing.assert_allclose(abs(r.dmrs()),1,atol=1e-14)


def test_invalid_bandwidth():
    with pytest.raises(ValueError):NRPUCCH3(NRCell(),n_prbs=7)


def test_resource_validation_boundaries():
    import numpy as np
    import pytest
    from cell import NRCell
    from grid import NRGrid
    from pucch import NRPUCCH3
    r=NRPUCCH3(NRCell())
    with pytest.raises(ValueError):r.map_to_grid(None,[0]*r.coded_length)
    with pytest.raises(TypeError):NRPUCCH3(None)
    with pytest.raises(TypeError):r.indices(dmrs=1)
    for kw in [dict(additional_dmrs=1),dict(modulation='16QAM'),dict(group_hopping='bad')]:
        with pytest.raises((ValueError,TypeError)):NRPUCCH3(r.cell,**kw)
    with pytest.raises(ValueError):r.generate([0])
    hopped=NRPUCCH3(r.cell,n_prbs=6,group_hopping='disable')
    np.testing.assert_allclose(abs(hopped.dmrs()),1,atol=1e-12)
