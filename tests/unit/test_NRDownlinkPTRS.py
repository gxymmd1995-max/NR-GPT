from dataclasses import replace
import numpy as np
import pytest
from cell import NRCell
from grid import NRGrid
from pdsch import NRPDSCH
from ptrs import NRDownlinkPTRS


@pytest.mark.parametrize("td", [1, 2, 4])
@pytest.mark.parametrize("fd", [2, 4])
@pytest.mark.parametrize("typ", [1, 2])
@pytest.mark.parametrize("offset", range(4))
def test_reference(td, fd, typ, offset):
    c = NRCell(n_size_grid=52, subcarrier_spacing_khz=30)
    r = NRPDSCH(c, dmrs_configuration_type=typ)
    p = NRDownlinkPTRS(r, td, fd, offset)
    idx = p.indices()
    x = p.generate()
    assert np.allclose(abs(x), 1)
    assert not set(idx[:, 1]) & set(r.dmrs_symbols)
    g = NRGrid(c, 1)
    p.map_to_grid(g)
    y = g.data * np.exp(0.4j)
    result = p.estimate_phase(y, np.ones(1))
    assert np.allclose(result["phase_rad"], 0.4)
    assert np.allclose(result["corrected_grid"], g.data)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"resource": None},
        {"time_density": 3},
        {"time_density": 0},
        {"frequency_density": 3},
        {"re_offset": 4},
    ],
)
def test_invalid(kwargs):
    args = dict(resource=NRPDSCH(NRCell()))
    args.update(kwargs)
    with pytest.raises((TypeError, ValueError)):
        NRDownlinkPTRS(**args)


def test_edges():
    c = NRCell(n_size_grid=52)
    r = NRPDSCH(c, n_prbs=3, dmrs_length=2)
    p = NRDownlinkPTRS(r, time_density=4)
    assert len(p.indices())
    with pytest.raises(ValueError):
        NRDownlinkPTRS(NRPDSCH(c, n_layers=2))
    with pytest.raises(ValueError):
        NRDownlinkPTRS(NRPDSCH(c, dmrs_length=2, dmrs_ports=(7,)))
    with pytest.raises(ValueError):
        p.map_to_grid(None)
    with pytest.raises(ValueError):
        p.estimate_phase(np.zeros((1, 1, 1)), [1])
    g = np.zeros((1, c.symbols_per_slot, c.n_subcarriers), complex)
    with pytest.raises(ValueError):
        p.estimate_phase(g, [0])
    with pytest.raises(ValueError):
        p.estimate_phase(g, [1])
    with pytest.raises(ValueError):
        p.estimate_phase(g, [np.nan])
