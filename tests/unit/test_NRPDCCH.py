import numpy as np
import pytest
from cell import NRCell
from grid import NRGrid
from pdcch import NRPDCCH

@pytest.mark.parametrize('duration,L',[(1,2),(1,6),(2,2),(3,3)])
@pytest.mark.parametrize('R',[2,3,6])
def test_reg_mapping(duration,L,R):
    r=NRPDCCH(NRCell(n_size_grid=108),frequency_resources=tuple(range(18)),duration=duration,mapping_type='interleaved',reg_bundle_size=L,interleaver_size=R,shift_index=17,dmrs_type_a_position=3)
    assert len(r.regs())==6
    assert len(set(r.regs()))==6
    assert r.indices().shape==(54,3) and r.indices(True).shape==(18,3)
    assert set(map(tuple,r.indices())).isdisjoint(map(tuple,r.indices(True)))
    np.testing.assert_allclose(abs(r.dmrs()),1,atol=1e-14)

@pytest.mark.parametrize('kw',[dict(cell=None),dict(cell=NRCell(n_start_grid=1)),dict(frequency_resources=()),dict(frequency_resources=(1,0)),dict(frequency_resources=(44,)),dict(duration=3),dict(aggregation_level=3),dict(cce_start=1,aggregation_level=2),dict(mapping_type='bad'),dict(reg_bundle_size=3),dict(interleaver_size=4),dict(mapping_type='interleaved',frequency_resources=(0,),duration=1,interleaver_size=6,reg_bundle_size=2)])
def test_invalid(kw):
    args=dict(cell=NRCell());args.update(kw)
    with pytest.raises((ValueError,TypeError)):NRPDCCH(**args)

def test_bad_mapping():
    r=NRPDCCH(NRCell())
    with pytest.raises(TypeError):r.indices(1)
    with pytest.raises(ValueError):r.generate([0])
    with pytest.raises(ValueError):r.map_to_grid(None,[0]*r.coded_length)
    grid=NRGrid(r.cell,1);r.map_to_grid(grid,[0]*r.coded_length)
    np.testing.assert_allclose(abs(r.generate([0]*r.coded_length)),1,atol=1e-14)
