from cell import NRCell
from pucch import NRPUCCH3, NRPUCCH3Transmitter


def test_long_uci():
    r = NRPUCCH3(NRCell(n_size_grid=24), n_prbs=3)
    out = NRPUCCH3Transmitter(r).transmit([0, 1] * 16)
    assert out["waveform"].shape == (1, r.cell.samples_per_slot)
    assert out["coded_bits"].shape == (r.coded_length,)


def test_shared_plotter_and_invalid_inputs():
    import numpy as np
    import pytest
    from cell import NRCell
    from diagnostics import NRPlotConfig, NRStagePlotter
    from pucch import NRPUCCH3, NRPUCCH3Transmitter, NRPUCCH3Receiver

    cell = NRCell(n_size_grid=12)
    r = NRPUCCH3(cell)
    trace = NRStagePlotter(NRPlotConfig(enabled=False))
    bits = [0, 1, 0]
    sent = NRPUCCH3Transmitter(r).transmit(bits, plotter=trace)
    rx = NRPUCCH3Receiver(r, len(bits))
    out = rx.receive(sent["waveform"], plotter=trace)
    assert out["detected"]
    with pytest.raises(TypeError):
        NRPUCCH3Transmitter(None)
    with pytest.raises(ValueError, match="0.6"):
        NRPUCCH3Transmitter(r).transmit([0] * int(0.8 * r.coded_length))
