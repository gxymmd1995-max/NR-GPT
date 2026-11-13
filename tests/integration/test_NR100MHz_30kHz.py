"""All implemented physical channels at FR1 100MHz/30kHz; no image output."""

import importlib.util
import logging
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest

CASES = [("pucch", "NRPUCCH" + str(i)) for i in range(5)] + [
    ("pusch", "NRPUSCH"),
    ("pdsch", "NRPDSCH"),
    ("pdcch", "NRPDCCH"),
    ("prach", "NRPRACH"),
    ("srs", "NRSRS"),
]


def _load_demo(module, name):
    path = (
        Path(__file__).resolve().parents[2]
        / "examples"
        / module
        / (name + "_100MHz_30kHz_demo.py")
    )
    spec = importlib.util.spec_from_file_location(name + "_100MHz", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.mark.parametrize("module,name", CASES)
def test_100mhz_time_channel(module, name):
    out = _load_demo(module, name).run_case()
    assert out["passed"]
    assert out["n_prbs"] == 273 and out["scs_khz"] == 30 and out["n_fft"] == 4096
    assert out["sample_rate_hz"] == 122880000


def _add_example_path(monkeypatch, module):
    monkeypatch.syspath_prepend(
        str(Path(__file__).resolve().parents[2] / "examples" / module)
    )


def test_100mhz_ssb(monkeypatch):
    _add_example_path(monkeypatch, "ssb")
    log = SimpleNamespace(logger=logging.getLogger(__name__))
    out = _load_demo("ssb", "NRSSB").run_case(log)
    assert out["crc_ok"] and out["detected"]
    assert (out["cell_id"], out["ssb_index"], out["sfn_lsb"]) == (1007, 7, 6)
    assert out["mib"] == [0, 1] * 12


@pytest.mark.parametrize(
    "module,name",
    [
        ("csirs", "NRCSIRS"),
        ("ptrs", "NRUplinkPTRS"),
        ("ptrs", "NRDownlinkPTRS"),
    ],
)
def test_100mhz_reference_signals(monkeypatch, module, name):
    _add_example_path(monkeypatch, module)
    out = _load_demo(module, name).run_case()
    cell = out["cell"]
    assert (cell.n_size_grid, cell.subcarrier_spacing_khz, cell.n_fft) == (
        273,
        30,
        4096,
    )
    assert cell.sample_rate_hz == 122880000
    if module == "csirs":
        np.testing.assert_allclose(
            out["channel_estimates"], [1 + 0.2j, 0.5 - 0.3j], atol=0.01
        )
    else:
        np.testing.assert_array_equal(out["correction_symbols"], np.arange(14))
        assert out["corrected_grid"][0, 1, 12 * 256 + 5] == pytest.approx(1 + 1j)
