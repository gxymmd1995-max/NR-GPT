"""DCI -> PDCCH/DMRS -> OFDM -> delay/CFO/SNR channel -> DCI and CRC."""
import numpy as np
from cell import NRCell
from channel import NRChannel
from diagnostics import ExampleLogger,NRPlotConfig,NRStagePlotter
from pdcch import NRPDCCH,NRPDCCHTransmitter,NRPDCCHReceiver

def main(log,plot_config=None):
    cell=NRCell(n_size_grid=24,n_rx_antennas=2)
    r=NRPDCCH(cell,frequency_resources=(0,1,2,3),aggregation_level=4,
        mapping_type='interleaved',reg_bundle_size=2,shift_index=7,scrambling_id=271,scrambling_rnti=4321)
    trace=NRStagePlotter(NRPlotConfig(enabled=True,channel='PDCCH') if plot_config is None else plot_config)
    bits=np.random.default_rng(42).integers(0,2,32).tolist()
    sent=NRPDCCHTransmitter(r,rnti=4321).transmit(bits,plotter=trace)
    wave=sent['waveform']*np.array([.7+.4j,-.3+.6j])[:,None]
    ch=NRChannel(cell);wave=ch.frequency_offset(ch.timing_advance(wave,-2),731,.23)
    wave,_=ch.add_awgn(wave,snr_db=25,seed=42)
    trace.record('channel.received',wave,title='2 Rx, delay2 samples, CFO731Hz, SNR25dB')
    out=NRPDCCHReceiver(r,len(bits),rnti=4321).receive(wave,known_delay_samples=2,
        known_frequency_offset_hz=731,known_initial_phase_rad=.23,plotter=trace)
    log.logger.info('PDCCH detected=%s CRC=%s bits_match=%s',out['detected'],out['crc_ok'],out['bits']==bits)
    trace.show()
    return out

if __name__=='__main__':
    with ExampleLogger(__file__) as run:main(run)
    import matplotlib.pyplot as plt
    plt.show()
