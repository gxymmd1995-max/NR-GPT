"""F0 OFDM发射、负SR静默、端口幅度与相位往返。"""

import numpy as np
import pytest

from cell import NRCell
from common import NROFDM
from pucch import NRPUCCH0,NRPUCCH0Transmitter


@pytest.mark.parametrize('n_symbols',[1,2])
def test_tx_grid_waveform_roundtrip_and_dtx(n_symbols):
    cell=NRCell(n_size_grid=6)
    r=NRPUCCH0(cell,n_symbols=n_symbols)
    tx=NRPUCCH0Transmitter(r,3500000123)
    out=tx.transmit([1,0],1,.7)
    assert out['waveform'].shape==(1,cell.samples_per_slot)
    assert out['active'] and out['m_cs']==10 and out['n_mapped_re']==12*n_symbols
    np.testing.assert_allclose(NROFDM(cell,3500000123).demodulate(out['waveform']),out['grid'].data,atol=2e-15)
    inactive=tx.transmit((),0)
    assert not inactive['active'] and inactive['m_cs'] is None
    assert not inactive['waveform'].any() and not inactive['grid'].occupancy.any()
    with pytest.raises(ValueError):tx.transmit([1],beta=float('nan'))


def test_transmitter_constructor_validation():
    with pytest.raises(TypeError):NRPUCCH0Transmitter(None)
    with pytest.raises(ValueError):NRPUCCH0Transmitter(NRPUCCH0(NRCell()),-1)
