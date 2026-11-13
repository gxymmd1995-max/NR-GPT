import numpy as np
import pytest
from common.NRLDPCCode import NRLDPCCode


@pytest.mark.parametrize("bg", [1, 2])
@pytest.mark.parametrize("z", [2, 3, 5, 7, 9, 11, 13, 15, 16])
def test_syndrome_and_decode(bg, z):
    c = NRLDPCCode(bg, z)
    b = np.random.default_rng(z).integers(0, 2, c.n_bits)
    x = c.encode(b)
    full = np.concatenate([b[: 2 * z], x])
    assert all(np.sum(full[r]) % 2 == 0 for r in c.check_rows())
    out = c.decode(20 * (1 - 2 * x))
    assert out["converged"]
    np.testing.assert_array_equal(out["bits"], b)


def test_invalid():
    with pytest.raises(ValueError):
        NRLDPCCode(3, 2)


def test_validation_and_corrupted_parity_equations(monkeypatch):
    import numpy as np
    import pytest
    from common.NRLDPCCode import NRLDPCCode

    for kw in [
        dict(lifting_size=1),
        dict(max_iterations=0),
        dict(normalization=0),
        dict(normalization=True),
    ]:
        args = dict(base_graph=2, lifting_size=2)
        args.update(kw)
        with pytest.raises(ValueError):
            NRLDPCCode(**args)
    c = NRLDPCCode(2, 2)
    for bits in [[0], np.full(c.n_bits, 2), np.zeros(c.n_bits, float)]:
        with pytest.raises(ValueError):
            c.encode(bits)
    for llr in [[0], np.full(c.code_length, np.nan)]:
        with pytest.raises(ValueError):
            c.decode(llr)
    for pos in [(-1,), (c.n_bits,)]:
        with pytest.raises(ValueError):
            c.decode(np.zeros(c.code_length), filler_positions=pos)
    monkeypatch.setattr(NRLDPCCode, "check_rows", lambda self: [np.array([0])])
    with pytest.raises(RuntimeError, match="inconsistent"):
        c.encode(np.ones(c.n_bits, int))
    monkeypatch.setattr(
        NRLDPCCode, "check_rows", lambda self: [np.array([c.n_bits])] * 2
    )
    with pytest.raises(RuntimeError, match="rank-deficient"):
        c.encode(np.zeros(c.n_bits, int))
