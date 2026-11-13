import numpy as np
import pytest
from common.NRDCICode import NRDCICode


@pytest.mark.parametrize(
    "a,e",
    [
        (12, 108),
        (32, 108),
        (64, 108),
        (140, 216),
        (32, 432),
        (140, 1728),
        (12, 48),
        (12, 140),
        (12, 84),
    ],
)
def test_roundtrip_and_wrong_rnti(a, e):
    c = NRDCICode(a, e, 4321)
    b = np.random.default_rng(a).integers(0, 2, a)
    llr = 20 * (1 - 2 * c.encode(b))
    o = c.decode(llr)
    assert o["bits"] == b.tolist() and o["crc_ok"]
    assert not NRDCICode(a, e, 4322).decode(llr)["crc_ok"]


def test_invalid_and_corrupted_table(monkeypatch):
    from pathlib import Path

    for args in [(11, 108), (32, 40), (32, 108, 65536)]:
        with pytest.raises((ValueError, TypeError)):
            NRDCICode(*args)
    c = NRDCICode(32, 108)
    with pytest.raises(ValueError):
        c.encode([0])
    with pytest.raises(ValueError):
        c.decode([float("nan")] * 108)
    monkeypatch.setattr(Path, "read_text", lambda *a, **kw: '{"reliability":[]}')
    with pytest.raises(ValueError, match="insufficient"):
        c.polar_configuration()
