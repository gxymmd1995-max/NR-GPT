import pytest
from cell import NRCell
from pucch import NRPUCCH2,NRPUCCH2Transmitter


def test_transmit():
    r=NRPUCCH2(NRCell(n_size_grid=6))
    out=NRPUCCH2Transmitter(r).transmit([1,0,1])
    assert out['waveform'].shape==(1,r.cell.samples_per_slot)
    with pytest.raises(ValueError):NRPUCCH2Transmitter(r).transmit([0]*12)


def test_reject_insufficient_prbs():
    r=NRPUCCH2(NRCell(n_size_grid=6))
    with pytest.raises(ValueError,match='code rate'):NRPUCCH2Transmitter(r).transmit([0]*11)
