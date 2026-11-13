import numpy as np
import pytest
from common.NRDLSCHCode import NRDLSCHCode


@pytest.mark.parametrize("a,rate", [(16, 0.5), (256, 0.5), (512, 0.8)])
@pytest.mark.parametrize("rv", range(4))
def test_limited_buffer_decode(a, rate, rv):
    base = NRDLSCHCode(a, rate, 5000, 2, rv)
    length = int(0.8 * base.ldpc().code_length)
    c = NRDLSCHCode(a, rate, 5000, 2, rv, n_ref=length)
    assert c.buffer_length == length
    assert np.all(c.rate_indices() < length)
    bits = np.random.default_rng(a).integers(0, 2, a)
    out = c.decode(20 * (1 - 2 * c.encode(bits)))
    assert out["crc_ok"] and out["converged"] and out["bits"] == bits.tolist()


@pytest.mark.parametrize("nref", [0, -1, True, 3.5])
def test_invalid_reference_buffer(nref):
    with pytest.raises((ValueError, TypeError)):
        NRDLSCHCode(256, 0.5, 4000, n_ref=nref)


@pytest.mark.parametrize("a", [16, 32, 80, 168, 256, 512, 3832, 8000])
@pytest.mark.parametrize("rv", range(4))
def test_smallest_buffer_retains_first_selectable_bit(a, rv):
    c = NRDLSCHCode(a, 0.8, 64, 2, rv, n_ref=1)
    assert 2 * c.lifting_size < a + c.crc_length
    np.testing.assert_array_equal(c.rate_indices(), np.zeros(64, dtype=int))


def test_all_supported_tb_sizes_keep_information_after_puncturing():
    # The supported byte-aligned TB domain and both BG-selection regions.
    # Ncb>=1 always contains circular-buffer index 0; 2Z<B ensures it is not filler.
    for a in range(16, 8425, 8):
        for rate in (0.2, 0.5, 0.8):
            b = a + (16 if a <= 3824 else 24)
            bg2 = a <= 292 or (a <= 3824 and rate <= 0.67) or rate <= 0.25
            if bg2 and b > 3840:
                with pytest.raises(ValueError, match="multiple LDPC"):
                    NRDLSCHCode(a, rate, 64)
            else:
                c = NRDLSCHCode(a, rate, 64)
                assert 2 * c.lifting_size < b
