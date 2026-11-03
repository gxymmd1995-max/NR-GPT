"""R15 F0资源、HARQ/SR表、位序、共享序列及原子映射。"""

from dataclasses import replace

import numpy as np
import pytest

from cell import NRCell
from grid import NRGrid
from pucch import NRPUCCH0


@pytest.mark.parametrize("bits,sr,shift",[
    ((0,),None,0),((1,),None,6),((0,),0,0),((1,),0,6),((0,),1,3),((1,),1,9),
    ((0,0),None,0),((0,1),None,3),((1,1),None,6),((1,0),None,9),
    ((0,0),1,1),((0,1),1,4),((1,1),1,7),((1,0),1,10),((),1,0),((),0,None)])
def test_harq_sr_original_tables_and_bit_order(bits,sr,shift):
    assert NRPUCCH0.cyclic_shift_offset(bits,sr)==shift


def test_resource_bwp_hop_coordinates_and_muted_sr():
    cell=NRCell(n_size_grid=24,n_start_grid=10,bwp_start=12,bwp_size=6)
    resource=NRPUCCH0(cell,prb=1,start_symbol=10,n_symbols=2,second_hop_prb=4)
    indices=resource.indices()
    np.testing.assert_array_equal(indices[:,0],0)
    np.testing.assert_array_equal(indices[:12,1],10)
    np.testing.assert_array_equal(indices[:12,2],np.arange(36,48))
    np.testing.assert_array_equal(indices[12:,2],np.arange(72,84))
    grid=NRGrid(cell)
    assert resource.map_to_grid(grid,(),sr=0)==0
    assert not grid.occupancy.any()
    assert resource.generate((),0).shape==(0,)
    assert resource.map_to_grid(grid,[1,0],1,beta=.7)==24
    np.testing.assert_allclose(abs(grid.extract(indices)),.7)
    assert np.all(grid.owners[grid.occupancy]=='PUCCH')
    before=grid.data
    with pytest.raises(ValueError):resource.map_to_grid(grid,[0])
    np.testing.assert_array_equal(grid.data,before)
    np.testing.assert_array_equal(resource.sequence_parameters()['hop'],[0,1])
    assert resource.to_dict()['antenna_port']==2000
    assert resource.to_dict()['second_hop_prb']==4


def test_single_port_unit_sequence_energy_orthogonality_and_defaults():
    resource=NRPUCCH0(NRCell(n_cell_id=17),hopping_id=None)
    assert resource.start_symbol==13 and resource.hopping_id==17
    x=resource.generate([0]);y=resource.generate([1])
    np.testing.assert_allclose(abs(x),1,atol=1e-15)
    assert abs(np.vdot(x,y))<1e-12
    assert x.shape==(12,)
    grid=NRGrid(resource.cell);resource.map_to_grid(grid,[0],beta=0)
    assert grid.occupancy.sum()==12 and not grid.data.any()
    x[:]=0
    assert np.linalg.norm(resource.generate([0]))>0
    ext=replace(resource,cell=NRCell(subcarrier_spacing_khz=60,cyclic_prefix='extended'),start_symbol=None)
    assert ext.start_symbol==11


@pytest.mark.parametrize("changes,error",[
    ({'cell':None},TypeError),({'n_symbols':0},ValueError),({'n_symbols':3},ValueError),
    ({'n_symbols':True},TypeError),({'start_symbol':14},ValueError),({'start_symbol':.5},TypeError),
    ({'prb':52},ValueError),({'prb':-1},ValueError),({'initial_cyclic_shift':12},ValueError),
    ({'group_hopping':'disable'},ValueError),({'hopping_id':1024},ValueError),({'hopping_id':True},TypeError),({'group_hopping':'groupHopping'},ValueError),
    ({'second_hop_prb':1},ValueError),({'n_symbols':2,'second_hop_prb':52},ValueError)])
def test_invalid_resource(changes,error):
    with pytest.raises(error):NRPUCCH0(**({'cell':NRCell()}|changes))


@pytest.mark.parametrize("bits,sr",[((),None),([0,1,0],None),([[1]],None),([2],None),([.0],None),([True],None),([True,0],None),([0,np.bool_(True)],None),([1],2)])
def test_invalid_payload(bits,sr):
    with pytest.raises(ValueError):NRPUCCH0.cyclic_shift_offset(bits,sr)


def test_grid_and_beta_validation():
    r=NRPUCCH0(NRCell())
    for grid in (None,NRGrid(NRCell(n_cell_id=2)),NRGrid(r.cell,2)):
        with pytest.raises(ValueError):r.map_to_grid(grid,[1])
    with pytest.raises(ValueError):r.map_to_grid(NRGrid(r.cell),[1],beta=-1)
    with pytest.raises(TypeError):r.generate([1],sr=True)
