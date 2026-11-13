import numpy as np
import pytest
from common.NRULSCHCode import NRULSCHCode


@pytest.mark.parametrize("a,rate", [(16, 0.5), (160, 0.5), (256, 0.5), (512, 0.8)])
@pytest.mark.parametrize("rv", range(4))
def test_crc_ldpc_rate_matching(a, rate, rv):
    codec = NRULSCHCode(a, rate, 5000, 2, rv)
    bits = np.random.default_rng(a).integers(0, 2, a)
    out = codec.decode(20 * (1 - 2 * codec.encode(bits)))
    assert out["crc_ok"] and out["converged"] and out["bits"] == bits.tolist()


def test_no_success_on_parity_only_nonconvergence():
    c = NRULSCHCode(512, 0.5, 1104, 2, 1)
    bits = np.random.default_rng(42).integers(0, 2, 512)
    out = c.decode(20 * (1 - 2 * c.encode(bits)))
    assert not out["converged"] and not out["crc_ok"]


@pytest.mark.parametrize(
    "args", [(17, 0.5, 1024), (4000, 0.2, 12000), (100, 0.5, 1001)]
)
def test_unsupported(args):
    with pytest.raises(ValueError):
        NRULSCHCode(*args)


def test_validation_boundaries():
    import numpy as np
    import pytest
    from common.NRULSCHCode import NRULSCHCode

    for kw in [dict(modulation_order=3), dict(output_length=65)]:
        args = dict(n_bits=16, target_code_rate=0.5, output_length=64)
        args.update(kw)
        with pytest.raises(ValueError):
            NRULSCHCode(**args)
    with pytest.raises(ValueError):
        NRULSCHCode.crc([0], 6)
    c = NRULSCHCode(16, 0.5, 64)
    for bits in [[0], np.full(16, 2), np.zeros(16, float)]:
        with pytest.raises(ValueError):
            c.encode(bits)
    for llr in [[0], np.full(64, np.nan)]:
        with pytest.raises(ValueError):
            c.decode(llr)
