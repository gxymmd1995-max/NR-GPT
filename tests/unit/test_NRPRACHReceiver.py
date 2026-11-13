import numpy as np
import pytest
from cell import NRCell
from channel import NRChannel
from prach import NRPRACH, NRPRACHTransmitter, NRPRACHReceiver
from diagnostics import NRPlotConfig, NRStagePlotter


@pytest.mark.parametrize(
    "fmt,scs",
    [
        ("0", 1.25),
        ("1", 1.25),
        ("2", 1.25),
        ("3", 5),
        ("A1", 15),
        ("C2", 30),
        ("B4", 60),
        ("C0", 120),
    ],
)
def test_waveform_noise_cfo_and_delay(fmt, scs):
    ul = 120 if scs >= 60 else 30
    cell = NRCell(n_size_grid=52, subcarrier_spacing_khz=ul, n_rx_antennas=2)
    r = NRPRACH(cell, preamble_format=fmt, subcarrier_spacing_khz=scs, guard_samples=32)
    h = np.array([0.7 + 0.4j, -0.3 + 0.6j])
    wave = h[:, None] * NRPRACHTransmitter(r).transmit(7)["waveform"]
    ch = NRChannel(cell)
    wave = ch.frequency_offset(ch.timing_advance(wave, -7), 731, 0.23)
    wave, _ = ch.add_awgn(wave, 25, seed=42)
    trace = NRStagePlotter(NRPlotConfig(enabled=True, channel="PRACH"))
    rx = NRPRACHReceiver(r, max_delay_samples=16)
    o = rx.receive(
        wave, known_frequency_offset_hz=731, known_initial_phase_rad=0.23, plotter=trace
    )
    assert o["best_preamble_index"] == 7 and len(o["detections"]) == 1
    d = o["detections"][0]
    assert d["delay_samples"] == 7 and d["delay_tc"] == 7 * cell.tc_per_sample
    assert d["delay_seconds"] == 7 / cell.sample_rate_hz
    np.testing.assert_allclose(d["channel_estimates"], h, atol=0.02)
    assert len(trace.stages) == 4
    zero = rx.receive(np.zeros_like(wave))
    assert not zero["detected"] and zero["best_preamble_index"] is None
    assert all(v["delay_samples"] is None for v in zero["candidates"])


def test_three_ues_different_cyclic_shifts():
    cell = NRCell(n_rx_antennas=2)
    r = NRPRACH(cell, guard_samples=32)
    ch = NRChannel(cell)
    wave = np.zeros((2, r.waveform_samples), complex)
    for index, delay, phase in [(0, 3, 0), (1, 7, 0.8), (2, 12, -0.7)]:
        sent = NRPRACHTransmitter(r).transmit(index)["waveform"]
        wave += (
            ch.timing_advance(sent, -delay)
            * np.array([np.exp(1j * phase), 0.8 * np.exp(-1j * phase)])[:, None]
        )
    wave, _ = ch.add_awgn(wave, 25, seed=42)
    out = NRPRACHReceiver(r).receive(wave)
    assert {(v["preamble_index"], v["delay_samples"]) for v in out["detections"]} == {
        (0, 3),
        (1, 7),
        (2, 12),
    }


@pytest.mark.parametrize(
    "kw",
    [
        dict(resource=None),
        dict(preamble_indices=[]),
        dict(preamble_indices=()),
        dict(preamble_indices=(0, 0)),
        dict(preamble_indices=(64,)),
        dict(max_delay_samples=-1),
        dict(max_delay_samples=500),
        dict(
            resource=NRPRACH(NRCell(), zero_correlation_zone=1), max_delay_samples=100
        ),
        dict(detection_threshold=1.1),
        dict(plot_config=1),
    ],
)
def test_invalid_receiver(kw):
    args = dict(resource=NRPRACH(NRCell()))
    args.update(kw)
    with pytest.raises((TypeError, ValueError)):
        NRPRACHReceiver(**args)


def test_invalid_waveform_and_ncs_zero():
    r = NRPRACH(NRCell(), zero_correlation_zone=0)
    rx = NRPRACHReceiver(r, preamble_indices=(0,), max_delay_samples=16)
    with pytest.raises(ValueError):
        rx.receive([[np.nan]])
    with pytest.raises(ValueError):
        rx.receive(np.zeros((1, 3)))
    out = rx.receive(NRPRACHTransmitter(r).transmit()["waveform"])
    assert out["detected"]
