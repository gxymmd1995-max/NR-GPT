"""F0完整时域闭环：UCI→NRGrid→OFDM→TA/传播/CFO/SNR噪声→OFDM/候选相关/DTX。"""

import json
from pathlib import Path

import numpy as np

from cell import NRCell
from channel import NRChannel
from diagnostics import ExampleLogger, NRPlotConfig, NRStagePlotter
from pucch import NRPUCCH0,NRPUCCH0Transmitter,NRPUCCH0Receiver


def main(log, plot_config: NRPlotConfig | None = None):
    """四类UCI，跳频、2Rx、显式已知同步补偿；SR负时用活动参考校准的背景噪声检查DTX。"""
    output=Path(__file__).resolve().parent
    config=NRPlotConfig(enabled=True,stages=('case0.*',)) if plot_config is None else plot_config
    cell=NRCell(n_cell_id=17,n_size_grid=24,n_start_grid=10,bwp_start=12,bwp_size=20,n_rx_antennas=2)
    resource=NRPUCCH0(cell,prb=1,start_symbol=10,n_symbols=2,initial_cyclic_shift=5,
                      hopping_id=731,group_hopping='enable',second_hop_prb=17)
    tx=NRPUCCH0Transmitter(resource,3500000123);model=NRChannel(cell)
    log.dump_state(cell,'cell');log.dump_state(resource,'resource');log.dump_state(tx,'transmitter');log.dump_state(model,'channel')
    gain=np.array([[1],[.6j]]);snr_db=-5.0;ta_samples=2;path_delay_samples=5;cfo=731;phase=.23
    payloads=[('HARQ1',[1],None),('HARQ2+SR',[1,0],1),('positive SR',[],1),('negative SR',[],0)]
    stored={};summaries=[];first_noise_reference=None;plot_stages=[]
    for index,(label,ack,sr) in enumerate(payloads):
        plotter=NRStagePlotter(config,prefix=f"case{index}")
        sent=tx.transmit(ack,sr,beta=.8,plotter=plotter)
        advanced=model.timing_advance(sent['waveform'],ta_samples)
        plotter.record('channel.ta',advanced,title='After TA advance: 2 NRCell samples')
        spatial=gain*advanced
        plotter.record('channel.spatial',spatial,title='One logical Tx port -> two physical Rx branches')
        delayed=model.timing_advance(spatial,-path_delay_samples)
        plotter.record('channel.path_delay',delayed,title='After propagation delay: 5 samples')
        offset=model.frequency_offset(delayed,cfo,phase)
        plotter.record('channel.cfo',offset,title='After CFO 731 Hz / initial phase 0.23 rad')
        if sent['active']:
            received,noise=model.add_awgn(offset,snr_db=snr_db,seed=20261027+index)
            if first_noise_reference is None:first_noise_reference=offset.copy()
        else:
            # DTX没有信号功率可定义SNR；背景噪声由首个活动PUCCH参考按同一SNR产生。
            _,noise=model.add_awgn(first_noise_reference,snr_db=snr_db,seed=20261027+index)
            received=offset+noise
        plotter.record('channel.noise',noise,title='Added complex AWGN; reference SNR -5 dB')
        plotter.record('channel.received',received,title='Received waveform after channel')
        receiver=NRPUCCH0Receiver(resource,len(ack),sr is not None,tx.carrier_frequency_hz)
        log.dump_state(receiver,label+' receiver')
        result=receiver.receive(received,known_delay_samples=path_delay_samples-ta_samples,
                               known_frequency_offset_hz=cfo,known_initial_phase_rad=phase,cp_fraction=.5,plotter=plotter)
        summary={key:value for key,value in result.items() if key not in ('rx_grid','rx_symbols','correlation_symbols','candidate_correlation_symbols')}
        summary.update({'label':label,'sent_harq_ack':ack,'sent_sr':sr,'active':sent['active'],
                        'noise_reference':'own active waveform' if sent['active'] else 'first active waveform for DTX background'})
        summaries.append(summary)
        for name,value in [('tx_waveform',sent['waveform']),('rx_waveform',received),('noise',noise),
                           ('tx_grid',sent['grid'].data),('rx_grid',result['rx_grid']),
                           ('correlation_symbols',result['correlation_symbols']),('candidate_correlation_symbols',result['candidate_correlation_symbols'])]:
            stored[f'case_{index}_{name}']=value
        log.logger.info('%s sent ACK=%s SR=%s; detected=%s ACK=%s SR=%s metric=%.6f threshold=%.2f',
                        label,ack,sr,result['detected'],result['harq_ack'],result['sr'],result['metric'],result['detection_threshold'])
        plot_stages.extend(plotter.stages)
        plotter.show()
    data={'resource':resource.to_dict(),'carrier_frequency_hz':tx.carrier_frequency_hz,
          'channel':{'snr_db':snr_db,'ta_samples':ta_samples,'path_delay_samples':path_delay_samples,
                     'net_delay_samples':path_delay_samples-ta_samples,'frequency_offset_hz':cfo,'initial_phase_rad':phase,
                     'rx_gain_real':gain.real.ravel().tolist(),'rx_gain_imag':gain.imag.ravel().tolist()},
          'plotting':{'enabled':config.enabled,'stages':config.stages,'max_points':config.max_points,'saved_images':False,'displayed_stages':plot_stages},
          'seed':20261027,'cases':summaries,'note':'Known synchronization; no blind CFO/timing. DTX uses noise calibrated from an active waveform; no direct noise-power API.'}
    (output/'NRPUCCH0_summary.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    np.savez_compressed(output/'NRPUCCH0_data.npz',**stored)
    return data


if __name__=='__main__':
    # 改此字段为False即可完全关闭绘图；stages=None显示四个UCI案例的全部阶段。
    plot_config=NRPlotConfig(enabled=True,stages=('case0.*',))
    with ExampleLogger(__file__) as run:main(run,plot_config)
    if plot_config.enabled:
        import matplotlib.pyplot as plt
        plt.show()  # 用户关闭图窗后退出；从不保存图像文件。
