import numpy as np
import pytest
from cell import NRCell
from grid import NRGrid
from pusch import NRPUSCH
from pdsch import NRPDSCH
from ptrs import NRUplinkPTRS, NRDownlinkPTRS


@pytest.mark.parametrize("td", [1, 2, 4])
@pytest.mark.parametrize("fd", [2, 4])
@pytest.mark.parametrize("typ", [1, 2])
@pytest.mark.parametrize("offset", range(4))
def test_reference(td, fd, typ, offset):
    c = NRCell(n_size_grid=52, subcarrier_spacing_khz=30)
    r = NRPUSCH(c, dmrs_configuration_type=typ)
    p = NRUplinkPTRS(r, td, fd, offset)
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
    args = dict(resource=NRPUSCH(NRCell()))
    args.update(kwargs)
    with pytest.raises((TypeError, ValueError)):
        NRUplinkPTRS(**args)


def test_edges():
    c = NRCell(n_size_grid=52)
    r = NRPUSCH(c, n_prbs=3, dmrs_length=2)
    p = NRUplinkPTRS(r, time_density=4)
    assert len(p.indices())
    with pytest.raises(ValueError):
        NRUplinkPTRS(NRPUSCH(c, n_layers=2))
    with pytest.raises(ValueError):
        NRUplinkPTRS(NRPUSCH(c, dmrs_length=2, dmrs_ports=(7,)))
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


@pytest.mark.parametrize(
    ("resource_type", "ptrs_type"),
    [
        (NRPUSCH, NRUplinkPTRS),
        (NRPDSCH, NRDownlinkPTRS),
    ],
)
def test_interpolated_cpe_corrects_payload_only_in_allocation(resource_type, ptrs_type):
    cell = NRCell(
        n_size_grid=12, n_start_grid=4, bwp_start=6, bwp_size=8, n_rx_antennas=2
    )
    resource = resource_type(cell, prb=1, n_prbs=4, start_symbol=1, n_symbols=12)
    ptrs = ptrs_type(resource, time_density=4)
    grid = NRGrid(cell, 1)
    ptrs.map_to_grid(grid)
    # Allocation begins at k=36. Its two PT-RS symbols are 1 and 6;
    # phases straddle the branch cut. The other user's REs must stay unchanged.
    grid.map([[0, 4, 37]], [1 - 1j], owner="payload")
    h = np.array([0.4 + 0.6j, -0.2 + 0.7j])
    symbols = ptrs.indices()[:, 1]
    expected = 3 + 0.18 * np.clip(
        np.arange(14) - symbols[0], 0, symbols[-1] - symbols[0]
    )
    rx = h[:, None, None] * grid.data * np.exp(1j * expected)[None, :, None]
    rx[:, 4, 35] = 2 + 3j
    rx[:, 0, 37] = 4 + 5j
    original = rx.copy()
    legacy = ptrs.estimate_phase(rx, h)
    out = ptrs.estimate_phase(rx, h, interpolate=True)
    assert 4 not in out["symbols"]
    assert out["phase_rad"][0] > 0 > out["phase_rad"][-1]
    np.testing.assert_array_equal(out["correction_symbols"], np.arange(1, 13))
    np.testing.assert_allclose(out["correction_phase_rad"], expected[1:13])
    np.testing.assert_allclose(out["corrected_grid"][:, 4, 37], h * (1 - 1j))
    np.testing.assert_array_equal(legacy["corrected_grid"][:, 4, 37], rx[:, 4, 37])
    np.testing.assert_array_equal(out["corrected_grid"][:, 4, 35], rx[:, 4, 35])
    np.testing.assert_array_equal(out["corrected_grid"][:, 0, 37], rx[:, 0, 37])
    np.testing.assert_array_equal(rx, original)
    with pytest.raises(TypeError, match="interpolate"):
        ptrs.estimate_phase(rx, h, interpolate=1)


def test_interpolation_without_ptrs_leaves_grid_unchanged():
    cell = NRCell()
    resource = NRPUSCH(cell, start_symbol=2, n_symbols=4, dmrs_length=2)
    ptrs = NRUplinkPTRS(resource, time_density=4)
    rx = np.ones((1, cell.symbols_per_slot, cell.n_subcarriers), dtype=complex)
    out = ptrs.estimate_phase(rx, [1], interpolate=True)
    assert not out["correction_symbols"].size
    np.testing.assert_array_equal(out["corrected_grid"], rx)
