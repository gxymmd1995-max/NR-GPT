import numpy as np
import pytest
from cell import NRCell
from prach import NRPRACH
from prach._tables import ROOTS_839, FORMATS, FREQUENCY


@pytest.mark.parametrize("fmt", list(FORMATS))
def test_zc_dft_and_cp(fmt):
    scs = FORMATS[fmt][3] or 15
    r = NRPRACH(NRCell(n_size_grid=52), preamble_format=fmt, subcarrier_spacing_khz=scs)
    x = r.sequence(31)
    s = r.generate(31)
    np.testing.assert_allclose(abs(x), 1, atol=1e-14)
    np.testing.assert_allclose(abs(s), np.sqrt(r.sequence_length), atol=1e-9)
    corr = np.fft.ifft(abs(np.fft.fft(x)) ** 2)
    np.testing.assert_allclose(corr[1:], 0, atol=1e-9)
    assert (
        r.cp_samples > 0 and r.active_samples == r.cp_samples + r.repetitions * r.n_fft
    )
    assert r.waveform_samples == r.active_samples


@pytest.mark.parametrize("ra,ul", list(FREQUENCY))
def test_r15_frequency_pairs(ra, ul):
    fmt = "0" if ra == 1.25 else "3" if ra == 5 else "A1"
    cell = NRCell(
        n_size_grid=52,
        subcarrier_spacing_khz=ul,
        n_start_grid=10,
        bwp_start=11,
        bwp_size=51,
    )
    r = NRPRACH(
        cell,
        preamble_format=fmt,
        subcarrier_spacing_khz=ra,
        frequency_start=1,
        frequency_index=1,
    )
    assert r.n_fft * ra * 1000 == cell.sample_rate_hz
    assert len(np.unique(r.frequency_bins % r.n_fft)) == r.sequence_length
    assert min(r.frequency_bins) >= -r.n_fft / 2 and max(r.frequency_bins) < r.n_fft / 2
    assert len(r.spectrum(63)) == r.n_fft


def test_tables_root_wrap_and_no_cyclic_shift():
    assert len(ROOTS_839) == 838 and sorted(ROOTS_839) == list(range(1, 839))
    assert ROOTS_839[:4] == (129, 710, 140, 699)
    r = NRPRACH(
        NRCell(),
        preamble_format="0",
        subcarrier_spacing_khz=1.25,
        root_sequence_index=837,
        zero_correlation_zone=0,
    )
    assert r.preamble_parameters(1) == (0, 129, 0)
    r = NRPRACH(NRCell(), root_sequence_index=137, zero_correlation_zone=0)
    assert r.preamble_parameters(1) == (0, 1, 0)
    assert r.preamble_parameters(0) == (137, 70, 0)


def test_half_ms_cp_extension_and_c2_long_cp():
    cell = NRCell(n_size_grid=52, subcarrier_spacing_khz=30)
    assert NRPRACH(cell, preamble_format="B4").cp_samples == 968
    assert (
        NRPRACH(cell, preamble_format="A1", occasion_start_samples=1000).cp_samples
        == 288
    )
    assert NRPRACH(cell, preamble_format="C2").cp_samples == 2064
    fr2 = NRCell(n_size_grid=52, subcarrier_spacing_khz=120)
    assert NRPRACH(fr2, subcarrier_spacing_khz=120).cp_samples == 208
    assert (
        NRPRACH(
            fr2,
            subcarrier_spacing_khz=120,
            time_origin_samples=fr2.sample_rate_hz // 8000,
        ).cp_samples
        == 144
    )


@pytest.mark.parametrize(
    "kw",
    [
        dict(cell=None),
        dict(preamble_format="D0"),
        dict(preamble_format=1),
        dict(subcarrier_spacing_khz=480),
        dict(subcarrier_spacing_khz=True),
        dict(preamble_format="0", subcarrier_spacing_khz=15),
        dict(cell=NRCell(subcarrier_spacing_khz=120), subcarrier_spacing_khz=15),
        dict(root_sequence_index=138),
        dict(zero_correlation_zone=16),
        dict(frequency_index=8),
        dict(frequency_start=50),
        dict(restricted_set="type_a"),
        dict(guard_samples=-1),
        dict(occasion_start_samples=-1),
    ],
)
def test_invalid_configuration(kw):
    args = dict(cell=NRCell())
    args.update(kw)
    with pytest.raises((ValueError, TypeError)):
        NRPRACH(**args)


def test_invalid_preamble_indices():
    r = NRPRACH(NRCell())
    for value in [-1, 64, True, 1.5]:
        with pytest.raises((ValueError, TypeError)):
            r.sequence(value)
