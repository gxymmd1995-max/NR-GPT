from cell import NRCell
from pdsch import NRPDSCH,NRPDSCHTransmitter


def test_transport_block_to_waveform():
    r=NRPDSCH(NRCell(n_size_grid=12),n_symbols=12)
    sent=NRPDSCHTransmitter(r).transmit([0,1]*128)
    assert sent['waveform'].shape==(1,r.cell.samples_per_slot)
    assert sent['coded_bits'].shape==(r.coded_length,)


def test_invalid_resource_and_insufficient_capacity():
    import pytest
    with pytest.raises(TypeError):NRPDSCHTransmitter(None)
    small=NRPDSCH(NRCell(n_size_grid=6),n_prbs=1,n_symbols=4)
    with pytest.raises(ValueError,match='insufficient'):NRPDSCHTransmitter(small).transmit([0]*256)
