from dataclasses import replace
import numpy as np
import pytest
from cell import NRCell
from grid import NRGrid
from common import NROFDM
from csirs import NRCSIRS


@pytest.mark.parametrize("row,density", [(1, 3), (2, 1), (2, 0.5)])
@pytest.mark.parametrize("parity", [0, 1])
def test_chain(row, density, parity):
    c = NRCell(n_size_grid=52, subcarrier_spacing_khz=30)
    r = NRCSIRS(c, row=row, density=density, rb_parity=parity, start_rb=1, n_rbs=3)
    x = r.generate()
    assert np.allclose(abs(x), 1)
    y = NROFDM(c).demodulate(r.waveform())
    assert np.allclose(r.estimate(y)["channel_estimates"], 1)
    g = NRGrid(c, 1)
    r.map_to_grid(g)
    with pytest.raises(ValueError):
        r.map_to_grid(g)
    with pytest.raises(ValueError):
        r.map_to_grid(None)
    with pytest.raises(ValueError):
        r.map_to_grid(NRGrid(c, 2))
    with pytest.raises(ValueError):
        r.estimate(np.zeros((1, 1, 1)))
    with pytest.raises(ValueError):
        r.estimate(y * np.nan)
    with pytest.raises(ValueError):
        replace(r, zero_power=True).estimate(y)
    assert not np.any(replace(r, zero_power=True).generate())
    empty = NRCSIRS(c, density=0.5, start_rb=1, n_rbs=1, rb_parity=0)
    assert empty.indices().shape == (0, 3)
    with pytest.raises(ValueError):
        empty.estimate(y)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"cell": None},
        {"row": 0},
        {"row": 3},
        {"row": True},
        {"start_rb": -1},
        {"n_rbs": 0},
        {"start_rb": 51, "n_rbs": 2},
        {"symbol": 1},
        {"symbol": 13},
        {"subcarrier": 12},
        {"row": 1, "subcarrier": 4},
        {"density": 2},
        {"row": 1, "density": 1},
        {"rb_parity": 2},
        {"scrambling_id": 1024},
        {"zero_power": 1},
        {"density": float("nan")},
    ],
)
def test_invalid(kwargs):
    args = dict(cell=NRCell(n_size_grid=52))
    args.update(kwargs)
    with pytest.raises((TypeError, ValueError)):
        NRCSIRS(**args)
