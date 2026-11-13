"""Fixed R15 CP-OFDM PT-RS; excludes transform precoding and hopping."""

import numpy as np
from common.NRCommon import _integer
from common import NRCommon
from common._validation import real_value
from grid import NRGrid

# 38.211 V15.2.0 tables 6.4.1.2.2.1-1 and 7.4.1.2.2-1.
OFFSETS = {
    1: ((0, 2, 6, 8), (2, 4, 8, 10), (1, 3, 7, 9), (3, 5, 9, 11)),
    2: (
        (0, 1, 6, 7),
        (1, 6, 7, 0),
        (2, 3, 8, 9),
        (3, 8, 9, 2),
        (4, 5, 10, 11),
        (5, 10, 11, 4),
    ),
}


def validate(obj, kind):
    if not isinstance(obj.resource, kind):
        raise TypeError("resource has wrong direction/type")
    r = obj.resource
    if r.n_layers != 1:
        raise ValueError("first release requires one layer")
    _integer("time_density", obj.time_density, 1, 4)
    if obj.time_density not in (1, 2, 4):
        raise ValueError("time_density must be 1/2/4")
    _integer("frequency_density", obj.frequency_density, 2, 4)
    if obj.frequency_density not in (2, 4):
        raise ValueError("frequency_density must be 2/4")
    _integer("re_offset", obj.re_offset, 0, 3)
    if r.dmrs_ports[0] >= len(OFFSETS[r.dmrs_configuration_type]):
        raise ValueError("associated DMRS port absent from R15 PTRS table")


def symbols(obj):
    r = obj.resource
    result = []
    ref = 0
    i = 0
    previous = -1
    dmrs = set(int(l) - r.start_symbol for l in r.dmrs_symbols)
    while ref + i * obj.time_density < r.n_symbols:
        target = ref + i * obj.time_density
        hit = [l for l in dmrs if max(previous + 1, ref) <= l <= target]
        if hit:
            ref = max(hit)
            i = 1
            previous = ref
        else:
            result.append(r.start_symbol + target)
            previous = target
            i += 1
    return np.array(result, dtype=int)


def positions(obj):
    r = obj.resource
    K = obj.frequency_density
    tail = r.n_prbs % K
    rb0 = r.rnti % (tail if tail else K)
    offset = OFFSETS[r.dmrs_configuration_type][r.dmrs_ports[0]][obj.re_offset]
    first = 12 * (r.cell.bwp_start - r.cell.n_start_grid + r.prb)
    return [
        (0, int(l), first + 12 * b + offset)
        for l in symbols(obj)
        for b in range(rb0, r.n_prbs, K)
    ]


def generate(obj):
    r = obj.resource
    indices = positions(obj)
    if not indices:
        return np.empty(0, dtype=complex)
    l = int(r.dmrs_symbols[0])
    nid = r.dmrs_scrambling_id
    seed = (
        2**17 * (r.cell.symbols_per_slot * r.cell.n_slot + l + 1) * (2 * nid + 1)
        + 2 * nid
        + r.n_scid
    ) % 2**31
    group, _, _ = r.port_parameters(r.dmrs_ports[0])
    absolute = np.array([k for _, _, k in indices]) + 12 * r.cell.n_start_grid
    if r.dmrs_configuration_type == 1:
        sequence_indices = (absolute - group) // 2
    else:
        sequence_indices = (absolute // 6) * 2 + (absolute % 6 - 2 * group)
    # All PT-RS symbols use the same first-DMRS Gold seed. Generate one
    # interval in bit coordinates, then gather the QPSK pairs in mapping order.
    first = int(sequence_indices.min())
    last = int(sequence_indices.max())
    gold = NRCommon.gold_sequence(seed, 2 * (last - first + 1), offset=2 * first)
    iq = 1 - 2 * gold.reshape(-1, 2)[sequence_indices - first].astype(int)
    return (iq[:, 0] + 1j * iq[:, 1]) / np.sqrt(2)


def mapping(obj, grid, beta):
    r = obj.resource
    if not isinstance(grid, NRGrid) or grid.cell != r.cell or grid.n_ports != 1:
        raise ValueError("matching single-port NRGrid required")
    return grid.map(
        obj.indices(), real_value("beta", beta, 0) * obj.generate(), owner="PTRS"
    )


def shared_channel_phase(obj, rx_grid, channel_by_rb, first_subcarrier):
    """Estimate CPE relative to one DM-RS symbol using per-RB [Rx,RB] LS gains."""
    r = obj.resource
    _, symbols_at_re, subcarriers = obj.indices().T
    # Grid coordinates are carrier-local; the LS channel axis is allocation-local RB.
    rb = (subcarriers - first_subcarrier) // 12
    measured = rx_grid[:, symbols_at_re, subcarriers]
    projection = (
        np.sum(channel_by_rb[:, rb].conj() * measured, axis=0) * obj.generate().conj()
    )
    combined = np.zeros(r.cell.symbols_per_slot, dtype=complex)
    np.add.at(combined, symbols_at_re, projection)
    valid = abs(combined) > 1e-20
    # The DM-RS LS channel already contains the phase of its own symbol.
    # Anchor that symbol to zero and unwrap in chronological order.
    valid[r.dmrs_symbols[0]] = True
    anchors = np.flatnonzero(valid)
    return np.interp(
        np.arange(r.cell.symbols_per_slot),
        anchors,
        np.unwrap(np.angle(combined[anchors])),
    )


def estimate(obj, rx_grid, channel_estimates, interpolate):
    r = obj.resource
    y = np.asarray(rx_grid, dtype=complex)
    h = np.asarray(channel_estimates, dtype=complex)
    if y.shape != (
        r.cell.n_rx_antennas,
        r.cell.symbols_per_slot,
        r.cell.n_subcarriers,
    ) or not np.all(np.isfinite(y)):
        raise ValueError("finite [Rx,symbol,k] required")
    if (
        h.shape != (r.cell.n_rx_antennas,)
        or not np.all(np.isfinite(h))
        or not np.any(abs(h) > 0)
    ):
        raise ValueError("nonzero finite flat [Rx] channel estimates required")
    if type(interpolate) is not bool:
        raise TypeError("interpolate must be bool")
    idx = obj.indices()
    x = obj.generate()
    ls = symbols(obj)
    phase = []
    for l in ls:
        mask = idx[:, 1] == l
        projection = np.sum(
            h.conj()[:, None] * y[:, idx[mask, 1], idx[mask, 2]] * x[mask].conj()
        )
        if abs(projection) < 1e-20:
            raise ValueError("PT-RS observation has no phase information")
        phase.append(np.angle(projection))
    phase = np.array(phase)
    corrected = y.copy()
    correction_symbols = ls
    correction_phase = phase
    if interpolate and ls.size:
        # Unwrap in time, interpolate between references, hold at the edges.
        # Restrict the rotation to this allocation so other users are untouched.
        correction_symbols = np.arange(r.start_symbol, r.start_symbol + r.n_symbols)
        correction_phase = np.interp(correction_symbols, ls, np.unwrap(phase))
        first = 12 * (r.cell.bwp_start - r.cell.n_start_grid + r.prb)
        corrected[:, correction_symbols, first : first + 12 * r.n_prbs] *= np.exp(
            -1j * correction_phase
        )[None, :, None]
    else:
        corrected[:, ls, :] *= np.exp(-1j * phase)[None, :, None]
    return dict(
        symbols=ls,
        phase_rad=phase,
        corrected_grid=corrected,
        correction_symbols=correction_symbols,
        correction_phase_rad=correction_phase,
    )
