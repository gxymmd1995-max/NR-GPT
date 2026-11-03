"""F2 long UCI uses common NRUCICode (Polar), not raw mother-code bits."""
import numpy as np
from cell import NRCell
from channel import NRChannel
from diagnostics import ExampleLogger,NRPlotConfig,NRStagePlotter
from pucch import NRPUCCH2,NRPUCCH2Transmitter,NRPUCCH2Receiver


def main(log,plot_config=None):
    cell=NRCell(n_size_grid=24,n_rx_antennas=2)
    r=NRPUCCH2(cell,prb=1,n_prbs=6,start_symbol=8,n_symbols=2,second_hop_prb=12,rnti=4321,data_scrambling_id=731,dmrs_scrambling_id=271)
    trace=NRStagePlotter(NRPlotConfig(enabled=True) if plot_config is None else plot_config)
    bits=np.random.default_rng(42).integers(0,2,32).tolist()
    tx=NRPUCCH2Transmitter(r).transmit(bits,plotter=trace)
    ch=NRChannel(cell);wave=tx['waveform']*np.array([.7+.4j,-.3+.6j])[:,None]
    wave=ch.frequency_offset(ch.timing_advance(wave,-2),731,.23)
    wave,_=ch.add_awgn(wave,snr_db=15,seed=42)
    trace.record('channel.received',wave,title='F2 Polar after delay / CFO / SNR noise')
    result=NRPUCCH2Receiver(r,len(bits)).receive(wave,known_delay_samples=2,known_frequency_offset_hz=731,known_initial_phase_rad=.23,plotter=trace)
    log.logger.info('F2 Polar bits_match=%s CRC=%s',bits==result['bits'],result['crc_ok'])
    trace.show()
    return result


if __name__=='__main__':
    with ExampleLogger(__file__) as run:main(run)
    import matplotlib.pyplot as plt
    plt.show()
