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


@pytest.mark.parametrize('type,length,ports',[(1,1,(0,1,2,3)),(1,2,(0,4,1,5)),(2,1,(2,3,4,5)),(2,2,(1,7,4,10))])
def test_dmrs_port_design_orthogonality(type,length,ports):
    r=NRPUSCH(NRCell(n_size_grid=12),n_prbs=2,n_layers=4,dmrs_configuration_type=type,
        dmrs_length=length,dmrs_ports=ports,dmrs_additional_position=1)
    coordinates=r.indices(True);values=r.dmrs();signatures={}
    for (layer,l,k),value in zip(coordinates,values):
        signatures.setdefault((l,k),np.zeros(4,complex))[layer]=value
    a=np.array(list(signatures.values()));gram=a.conj().T@a
    np.testing.assert_allclose(gram,np.diag(np.diag(gram)),atol=1e-12)
    assert np.linalg.matrix_rank(a)==4


def test_additional_positions_and_rejections():
    cell=NRCell(n_size_grid=12)
    np.testing.assert_array_equal(NRPUSCH(cell,n_symbols=12,dmrs_additional_position=3).dmrs_symbols,[2,5,8,11])
    np.testing.assert_array_equal(NRPUSCH(cell,dmrs_length=2,dmrs_additional_position=1).dmrs_symbols,[2,3,10,11])
    for kwargs in [dict(n_layers=5),dict(n_layers=2,dmrs_ports=(0,0)),dict(dmrs_length=1,dmrs_ports=(4,)),
        dict(n_layers=3,cdm_groups_without_data=1),dict(dmrs_length=2,dmrs_additional_position=2),
        dict(dmrs_type_a_position=3,dmrs_additional_position=3)]:
        with pytest.raises(ValueError):NRPUSCH(cell,**kwargs)


def test_reject_malformed_mapping_inputs():
    from grid import NRGrid
    r=NRPUSCH(NRCell(n_size_grid=12))
    with pytest.raises(ValueError):r.generate([0,1])
    with pytest.raises(TypeError):r.indices(dmrs=1)
    with pytest.raises(ValueError):r.map_to_grid(NRGrid(NRCell(n_size_grid=6),1),[0]*r.coded_length)


@pytest.mark.parametrize('kwargs',[
    dict(cell=None),dict(dmrs_ports=[0]),dict(dmrs_ports=(False,)),
    dict(n_symbols=4,start_symbol=0,dmrs_length=2,dmrs_type_a_position=3),
    dict(dmrs_scrambling_id=65536),dict(data_scrambling_id=-1),
])
def test_invalid_configuration(kwargs):
    config=dict(cell=NRCell(n_size_grid=12));config.update(kwargs)
    with pytest.raises((ValueError,TypeError)):NRPUSCH(**config)


def test_short_allocation_additional_position_falls_back_to_first_dmrs():
    r=NRPUSCH(NRCell(),n_symbols=4,dmrs_additional_position=1)
    np.testing.assert_array_equal(r.dmrs_symbols,[2])
