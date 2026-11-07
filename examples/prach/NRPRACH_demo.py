"""Three simultaneous PRACH preambles separated by cyclic shifts; plots display only."""
import numpy as np
from cell import NRCell
from channel import NRChannel
from diagnostics import ExampleLogger,NRPlotConfig,NRStagePlotter
from prach import NRPRACH,NRPRACHTransmitter,NRPRACHReceiver


def main(log, plot_config=None):
    cell=NRCell(n_size_grid=52,subcarrier_spacing_khz=30,n_rx_antennas=2)
    resource=NRPRACH(cell,preamble_format='A1',subcarrier_spacing_khz=15,
                     root_sequence_index=0,zero_correlation_zone=8,guard_samples=32)
    trace=NRStagePlotter(NRPlotConfig(enabled=True,channel='PRACH') if plot_config is None else plot_config)
    channel=NRChannel(cell);received=np.zeros((2,resource.waveform_samples),complex)
    expected={0:3,1:7,2:12}
    for index,delay in expected.items():
        sent=NRPRACHTransmitter(resource).transmit(index,plotter=trace)
        phase=.7*index
        gains=np.array([np.exp(1j*phase),.8*np.exp(-1j*phase)])
        received+=gains[:,None]*channel.timing_advance(sent['waveform'],-delay)
        log.logger.info('PRACH preamble=%s (logical,u,C)=%s delay_samples=%s',index,
                        resource.preamble_parameters(index),delay)
    received=channel.frequency_offset(received,731,.23)
    received,_=channel.add_awgn(received,snr_db=25,seed=42)
    trace.record('channel.received',received,title='3 PRACH UEs, 2 Rx, CFO731Hz, SNR25dB')
    out=NRPRACHReceiver(resource,max_delay_samples=16).receive(received,
        known_frequency_offset_hz=731,known_initial_phase_rad=.23,plotter=trace)
    actual={v['preamble_index']:v['delay_samples'] for v in out['detections']}
    log.logger.info('PRACH expected=%s detected=%s match=%s',expected,actual,expected==actual)
    trace.show()
    return out


if __name__=='__main__':
    with ExampleLogger(__file__) as run:main(run)
    import matplotlib.pyplot as plt
    plt.show()
