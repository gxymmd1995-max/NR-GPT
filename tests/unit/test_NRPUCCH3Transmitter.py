from cell import NRCell
from pucch import NRPUCCH3,NRPUCCH3Transmitter


def test_long_uci():
    r=NRPUCCH3(NRCell(n_size_grid=24),n_prbs=3)
    out=NRPUCCH3Transmitter(r).transmit([0,1]*16)
    assert out['waveform'].shape==(1,r.cell.samples_per_slot)
    assert out['coded_bits'].shape==(r.coded_length,)
