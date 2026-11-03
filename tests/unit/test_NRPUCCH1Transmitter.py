import pytest
from cell import NRCell
from pucch import NRPUCCH1,NRPUCCH1Transmitter


def test_waveform_shape():
    cell=NRCell(n_size_grid=6)
    assert NRPUCCH1Transmitter(NRPUCCH1(cell)).transmit([0])['waveform'].shape==(1,cell.samples_per_slot)
    with pytest.raises(TypeError):NRPUCCH1Transmitter(None)
