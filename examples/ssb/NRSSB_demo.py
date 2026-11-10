"""One SS/PBCH block; known occasion with blind PCI/index acquisition, display only."""
from dataclasses import replace
import numpy as np
from cell import NRCell
from channel import NRChannel
from diagnostics import ExampleLogger,NRPlotConfig,NRStagePlotter
from ssb import NRSSB,NRSSBTransmitter,NRSSBReceiver

def main(log,plot_config=None,n_size_grid=24):
    cell=NRCell(n_cell_id=1007,n_size_grid=n_size_grid,n_rx_antennas=2)
    r=NRSSB(cell,start_subcarrier=24,l_max=8,ssb_index=7,half_frame=1,k_ssb=23)
    mib=[0,1]*12;trace=NRStagePlotter(NRPlotConfig(enabled=True,channel='SSB') if plot_config is None else plot_config)
    sent=NRSSBTransmitter(r).transmit(mib,sfn_lsb=6,plotter=trace)
    ch=NRChannel(cell);wave=sent['waveform']*np.array([.7+.4j,-.3+.6j])[:,None]
    wave=ch.frequency_offset(ch.timing_advance(wave,-2),731,.23);wave,_=ch.add_awgn(wave,25,seed=42)
    trace.record('channel.received',wave,title='SSB: 2 Rx, delay2 samples, CFO731Hz, SNR25dB')
    unknown=replace(r,cell=replace(cell,n_cell_id=0),ssb_index=0)
    out=NRSSBReceiver(unknown).receive(wave,known_delay_samples=2,known_frequency_offset_hz=731,known_initial_phase_rad=.23,plotter=trace)
    log.logger.info('SSB PCI=%s index=%s MIB_match=%s SFN_LSB=%s CRC=%s',out['cell_id'],out['ssb_index'],out['mib']==mib,out['sfn_lsb'],out['crc_ok'])
    trace.show()
    return out

if __name__=='__main__':
    with ExampleLogger(__file__) as log:main(log)
    import matplotlib.pyplot as plt
    plt.show()
