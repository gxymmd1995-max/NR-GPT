import pytest
from cell import NRCell
from pucch import NRPUCCH4,NRPUCCH4Transmitter


def test_time_waveform_and_rate():
    r=NRPUCCH4(NRCell(n_size_grid=6),spreading_factor=4,occ_index=3)
    sent=NRPUCCH4Transmitter(r).transmit([0,1,0,1,1,0,1])
    assert sent['waveform'].shape==(1,r.cell.samples_per_slot)
    with pytest.raises(ValueError):NRPUCCH4Transmitter(r).transmit([0]*100)
