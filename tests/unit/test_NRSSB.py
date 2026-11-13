import numpy as np
import pytest
from cell import NRCell
from grid import NRGrid
from ssb import NRSSB


@pytest.mark.parametrize("pci", [0, 1, 2, 335, 1007])
def test_geometry_sequences_and_reserved_zeros(pci):
    r = NRSSB(NRCell(n_cell_id=pci, n_size_grid=24), start_subcarrier=24)
    assert [len(r.indices(k)) for k in ["pss", "sss", "pbch", "dmrs"]] == [
        127,
        127,
        432,
        144,
    ]
    coords = np.concatenate([r.indices(k) for k in ["pss", "sss", "pbch", "dmrs"]])
    assert len(set(map(tuple, coords))) == 830
    assert set(r.pss(pci % 3)) == {-1, 1} and set(r.sss(pci)) == {-1, 1}
    np.testing.assert_allclose(abs(r.dmrs()), 1, atol=1e-14)
    g = NRGrid(r.cell, 1)
    r.map_to_grid(g, [0] * 864)
    assert np.count_nonzero(g.occupancy) == 960
    assert np.count_nonzero(g.data) == 830


@pytest.mark.parametrize(
    "cell",
    [
        None,
        NRCell(subcarrier_spacing_khz=60),
        NRCell(subcarrier_spacing_khz=60, cyclic_prefix="extended"),
    ],
)
def test_invalid_cell(cell):
    with pytest.raises((ValueError, TypeError)):
        NRSSB(cell)


def test_invalid_methods():
    r = NRSSB(NRCell())
    with pytest.raises(ValueError):
        r.indices("bad")
    with pytest.raises(ValueError):
        r.generate([0])
    with pytest.raises(ValueError):
        r.map_to_grid(None, [0] * 864)
    with pytest.raises(ValueError):
        NRSSB.pss(3)
    with pytest.raises(ValueError):
        NRSSB.sss(1008)


@pytest.mark.parametrize("scs,lmax", [(30, 64), (120, 8)])
def test_r15_frequency_range_pair(scs, lmax):
    with pytest.raises(ValueError, match="Lmax64"):
        NRSSB(NRCell(subcarrier_spacing_khz=scs), l_max=lmax)
