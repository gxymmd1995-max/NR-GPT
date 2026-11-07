import numpy as np
import pytest
from cell import NRCell
from prach import NRPRACH,NRPRACHTransmitter
from diagnostics import NRPlotConfig,NRStagePlotter


def test_waveform_cp_offset_scaling_and_trace():
    r=NRPRACH(NRCell(),preamble_format='C2',occasion_start_samples=19,guard_samples=23)
    trace=NRStagePlotter(NRPlotConfig(enabled=True,channel='PRACH'))
    o=NRPRACHTransmitter(r).transmit(17,.5,plotter=trace)
    w=o['waveform'][0];u=.5*r.useful_waveform(17);first=r.occasion_start_samples
    np.testing.assert_array_equal(w[:first],0);np.testing.assert_array_equal(w[-23:],0)
    np.testing.assert_allclose(w[first:first+r.cp_samples],u[np.arange(-r.cp_samples,0)%r.n_fft])
    np.testing.assert_allclose(w[first+r.cp_samples:-23],np.tile(u,r.repetitions))
    assert len(trace.stages)==5
    np.testing.assert_array_equal(NRPRACHTransmitter(r).transmit(17,0)['waveform'],0)


def test_bad_transmitter_inputs():
    with pytest.raises(TypeError):NRPRACHTransmitter(None)
    with pytest.raises(TypeError):NRPRACHTransmitter(NRPRACH(NRCell()),plot_config=1)
    with pytest.raises(ValueError):NRPRACHTransmitter(NRPRACH(NRCell())).transmit(beta=-1)
