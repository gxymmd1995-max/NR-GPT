"""重算实际MATLAB输入，比较F0序列/坐标/OFDM/时域信道/接收决策与Toolbox输出。"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np

from cell import NRCell
from channel import NRChannel
from diagnostics import ExampleLogger
from pucch import NRPUCCH0, NRPUCCH0Transmitter, NRPUCCH0Receiver


def resource_from_input(data):
    """JSON中的-1表示未配置second_hop_prb；cell字段独立恢复，避免修改原始输入。"""
    names=('prb','start_symbol','n_symbols','initial_cyclic_shift','hopping_id','group_hopping')
    return NRPUCCH0(NRCell(**data['cell']),**{key:data[key] for key in names},
                    second_hop_prb=None if data['second_hop_prb']<0 else data['second_hop_prb'])


def compare(logger=None, write_report=True):
    """任何断言失败均不输出成功报告；参考必须由MATLAB独立导出，报告不冒充MATLAB结果。"""
    output=Path(__file__).resolve().parent;root=output.parents[1]
    path=output/'NRPUCCH0_reference.json'
    reference=json.loads(path.read_text(encoding='utf-8-sig'))
    assert reference['matlab_version'] and reference['toolbox']
    max_sequence=max_wave=max_received=max_metric=max_correlation=0.0
    decisions=[]
    default_difference_count=0;max_default_difference=0.0
    for case in reference['sequence_cases']:
        x,e=case['input'],case['expected'];resource=resource_from_input(x)
        ack=np.atleast_1d(x['harq_ack']).astype(int).tolist();sr=None if x['sr']<0 else x['sr']
        actual=resource.generate(ack,sr);expected=np.array(e['real'])+1j*np.array(e['imag'])
        np.testing.assert_allclose(actual,expected,rtol=0,atol=5e-13)
        np.testing.assert_array_equal(resource.indices(),e['indices'])
        max_sequence=max(max_sequence,float(np.max(abs(actual-expected),initial=0)))
        raw=np.array(e['toolbox_default_real'])+1j*np.array(e['toolbox_default_imag'])
        difference=float(np.max(abs(raw-expected),initial=0))
        default_difference_count+=int(difference>5e-13)
        max_default_difference=max(max_default_difference,difference)
    for index,case in enumerate(reference['waveform_cases']):
        x,e=case['input'],case['expected'];config=x['resource'];resource=resource_from_input(config)
        ack=np.atleast_1d(config['harq_ack']).astype(int).tolist();sr=None if config['sr']<0 else config['sr']
        def wave(prefix,branches):
            return (np.array(e[prefix+'real'])+1j*np.array(e[prefix+'imag'])).reshape(branches,e['n_samples'])
        tx=NRPUCCH0Transmitter(resource,x['carrier_frequency_hz']).transmit(ack,sr,x['beta'])['waveform']
        np.testing.assert_allclose(tx,wave('tx_',1),rtol=0,atol=2e-9)
        max_wave=max(max_wave,float(np.max(abs(tx-wave('tx_',1)))))
        model=NRChannel(resource.cell)
        clean=tx*np.array([[1],[.6j]])
        delayed=model.timing_advance(clean,-x['delay_samples'])
        offset=model.frequency_offset(delayed,x['frequency_offset_hz'],x['initial_phase_rad'])
        standard=(np.array(x['standard_real'])+1j*np.array(x['standard_imag'])).reshape(offset.shape)
        received,_=model.add_awgn(offset,x['snr_db'],noise_standard=standard)
        np.testing.assert_allclose(received,wave('rx_',2),rtol=0,atol=2e-9)
        max_received=max(max_received,float(np.max(abs(received-wave('rx_',2)))))
        # 解码实际MATLAB接收波形，不把Python发射输出充当接收参考。
        result=NRPUCCH0Receiver(resource,len(ack),sr is not None,x['carrier_frequency_hz']).receive(
            wave('rx_',2),known_delay_samples=x['delay_samples'],
            known_frequency_offset_hz=x['frequency_offset_hz'],known_initial_phase_rad=x['initial_phase_rad'])
        target=e['decision'];assert result['detected']==target['detected']
        expected_correlations=np.array(target['correlation_real'])+1j*np.array(target['correlation_imag'])
        np.testing.assert_allclose(result['candidate_correlation_symbols'].ravel(),expected_correlations,rtol=0,atol=2e-9)
        max_correlation=max(max_correlation,float(np.max(abs(result['candidate_correlation_symbols'].ravel()-expected_correlations))))
        assert result['harq_ack']==(ack if target['detected'] else None)
        assert result['sr']==(sr if target['detected'] else 0)
        np.testing.assert_allclose(result['metric'],target['metric'],rtol=0,atol=2e-9)
        np.testing.assert_allclose(result['resource_power'],target['resource_power'],rtol=1e-7,atol=1e-12)
        np.testing.assert_allclose([c['metric'] for c in result['candidates']],
                                   [c['metric'] for c in np.atleast_1d(target['candidates'])],atol=2e-9,rtol=0)
        # 同时记录/核对Toolbox自己的F0译码输出；指标算法独立，不要求与原生MATLAB指标相同。
        toolbox_ack=np.atleast_1d(e['toolbox_bits'][0]).astype(int).tolist()
        toolbox_sr=e['toolbox_bits'][1]
        assert toolbox_ack==ack
        assert toolbox_sr==([] if sr is None else sr)
        max_metric=max(max_metric,abs(result['metric']-target['metric']))
        decisions.append({'case':index,'harq_ack':result['harq_ack'],'sr':result['sr'],
                          'detected':result['detected'],'metric':result['metric'],
                          'toolbox_bits':e['toolbox_bits'],'toolbox_metric':e['toolbox_metric']})
    files=[path,output/'export_NRPUCCH0_reference.m',output/'compare_NRPUCCH0_reference.py',
           root/'src/pucch/NRPUCCH0.py',root/'src/pucch/NRPUCCH0Transmitter.py',root/'src/pucch/NRPUCCH0Receiver.py',
           root/'src/common/NRCommon.py',root/'src/common/_low_papr_tables.py',root/'src/common/NROFDM.py',
           root/'src/common/NRPhaseRotation.py',root/'src/channel/NRChannel.py',
           root/'src/diagnostics/NRPlotConfig.py',root/'src/diagnostics/NRStagePlotter.py']
    report={'status':'passed','generated_at':datetime.now(timezone.utc).isoformat(),
            'matlab_version':reference['matlab_version'],'toolbox':reference['toolbox'],
            'sequence_case_count':len(reference['sequence_cases']),'waveform_case_count':len(decisions),
            'max_sequence_abs_error':max_sequence,'max_tx_waveform_abs_error':max_wave,
            'max_received_waveform_abs_error':max_received,'max_detection_metric_abs_error':max_metric,'max_correlation_symbol_abs_error':max_correlation,
            'sequence_adapter':reference['sequence_adapter'],
            'toolbox_default_sequence_difference_count':default_difference_count,
            'max_toolbox_default_sequence_difference':max_default_difference,
            'index_mismatch_count':0,'decision_mismatch_count':0,'toolbox_uci_mismatch_count':0,
            'hashes':{str(p.relative_to(root)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
            'note':'Python comparison of actual independent MATLAB references. Native MATLAB receiver metric and Toolbox UCI bits both retained.',
            'cases':decisions}
    if write_report:
        (output/'NRPUCCH0_comparison.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    if logger is not None:
        logger.info('PASS: %d sequence/RE, %d waveform/receiver cases; max sequence error %.3g',
                    report['sequence_case_count'],report['waveform_case_count'],max_sequence)
    return report


if __name__=='__main__':
    with ExampleLogger(__file__) as run:
        compare(run.logger)
