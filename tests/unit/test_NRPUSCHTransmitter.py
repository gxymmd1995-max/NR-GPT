from cell import NRCell
from pusch import NRPUSCH,NRPUSCHTransmitter


def test_transport_to_time_waveform():
    r=NRPUSCH(NRCell(n_size_grid=12),n_symbols=12)
    out=NRPUSCHTransmitter(r).transmit([0,1]*128)
    assert out['waveform'].shape==(1,r.cell.samples_per_slot)
    assert out['coded_bits'].shape==(r.coded_length,)
