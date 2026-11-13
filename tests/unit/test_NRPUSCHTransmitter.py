from cell import NRCell
from pusch import NRPUSCH, NRPUSCHTransmitter


def test_transport_to_time_waveform():
    r = NRPUSCH(NRCell(n_size_grid=12), n_symbols=12)
    out = NRPUSCHTransmitter(r).transmit([0, 1] * 128)
    assert out["waveform"].shape == (1, r.cell.samples_per_slot)
    assert out["coded_bits"].shape == (r.coded_length,)


def test_reject_resource_and_insufficient_capacity():
    import pytest

    with pytest.raises(TypeError):
        NRPUSCHTransmitter(None)
    resource = NRPUSCH(NRCell(n_size_grid=12), n_prbs=1, n_symbols=4)
    with pytest.raises(ValueError, match="insufficient"):
        NRPUSCHTransmitter(resource).transmit([0, 1] * 128)
