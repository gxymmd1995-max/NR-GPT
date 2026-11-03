"""PUCCH F0时域接收：显式已知同步补偿、OFDM、UCI候选非相干相关及DTX。

F0没有独立DMRS，本实现按每符号/每Rx的12点平坦信道近似做相关，非规范强制接收算法。
"""

from dataclasses import dataclass
from itertools import product

import numpy as np

from channel import NRChannel
from diagnostics import NRPlotConfig, NRStagePlotter
from common import NROFDM
from common.NRCommon import _integer
from common._validation import real_value, waveform_array
from pucch.NRPUCCH0 import NRPUCCH0


@dataclass(frozen=True, slots=True)
class NRPUCCH0Receiver:
    """已知资源、HARQ位数/SR机会的单UE接收机；不做盲资源搜索或多用户联合检测。"""

    resource: NRPUCCH0
    n_harq_ack_bits: int = 1
    sr_enabled: bool = False
    carrier_frequency_hz: float = 0.0
    detection_threshold: float | None = None
    plot_config: NRPlotConfig | None = None

    def __post_init__(self):
        if not isinstance(self.resource, NRPUCCH0):
            raise TypeError("resource must be NRPUCCH0")
        _integer("n_harq_ack_bits", self.n_harq_ack_bits, 0, 2)
        if type(self.sr_enabled) is not bool:
            raise TypeError("sr_enabled must be bool")
        if self.n_harq_ack_bits == 0 and not self.sr_enabled:
            raise ValueError("receiver must expect HARQ-ACK and/or an SR occasion")
        if self.detection_threshold is None:
            object.__setattr__(self, "detection_threshold", .49 if self.resource.n_symbols == 1 else .42)
        real_value("detection_threshold", self.detection_threshold, 0, 1)
        NROFDM(self.resource.cell, self.carrier_frequency_hz)
        NRStagePlotter(self.plot_config)

    def _hypotheses(self) -> list[tuple[tuple[int,...], int | None]]:
        """合法UCI假设，HARQ位序与SR0/1次序固定；SR-only仅枚举正SR。"""
        acks=product((0,1),repeat=self.n_harq_ack_bits)
        srs=(1,) if self.n_harq_ack_bits==0 else ((0,1) if self.sr_enabled else (None,))
        return [(bits,sr) for bits in acks for sr in srs]

    @staticmethod
    def validate_cyclic_shift_group(receivers: dict) -> dict[str, list[int]]:
        """检查共用时频/根/Gold配置的CDM组；全部合法UCI对应的(m0+m_cs)mod12不得相撞。

        只验证循环移位分配，不能保证未知定时/CFO/强频选信道下仍正交；不是联合解码或功控。
        返回每用户所有候选移位号，无量纲，尚未加共同逐符号n_cs。
        """
        if not isinstance(receivers,dict) or not receivers:
            raise ValueError("receivers must be a nonempty user ID -> NRPUCCH0Receiver dict")
        fields=("cell","prb","start_symbol","n_symbols","hopping_id","group_hopping","second_hop_prb")
        signature=None;occupied={};allocation={}
        for uid,receiver in receivers.items():
            if not isinstance(uid,str) or not uid.strip() or not isinstance(receiver,NRPUCCH0Receiver):
                raise ValueError("each user ID must be nonblank and each value an NRPUCCH0Receiver")
            resource=receiver.resource
            current=tuple(getattr(resource,field) for field in fields)
            if signature is None:
                signature=current
            elif current!=signature:
                raise ValueError("a cyclic-shift group must share cell, time/frequency resources and hopping identity/mode")
            shifts=sorted({(resource.initial_cyclic_shift+resource.cyclic_shift_offset(bits,sr))%12
                           for bits,sr in receiver._hypotheses()})
            for shift in shifts:
                if shift in occupied:
                    raise ValueError(f"cyclic-shift collision: {uid} and {occupied[shift]} both use candidate {shift}")
                occupied[shift]=uid
            allocation[uid]=shifts
        return allocation

    def receive(self, waveform: np.ndarray, *, known_frequency_offset_hz: float = 0.0,
                known_initial_phase_rad: float = 0.0, known_delay_samples: int = 0,
                cp_fraction: float = 1.0, plotter=None) -> dict:
        """接收cell.n_rx_antennas支路的完整当前slot[Rx,T]；仅对显式已知同步量作补偿。

        正known_delay_samples表示待消除的实际延迟，采用非循环提前；有限窗口已丢样点不可恢复。
        非相干合并不同符号/跳段/Rx的相关功率，可适应每个符号不同的未知复增益。
        """
        values = waveform_array(waveform)
        cell = self.resource.cell
        if values.shape != (cell.n_rx_antennas, cell.samples_per_slot):
            raise ValueError("waveform must have shape [cell.n_rx_antennas, cell.samples_per_slot]")
        trace = NRStagePlotter(self.plot_config) if plotter is None else plotter
        trace.record("rx.input_waveform",values,title="Waveform after channel")
        channel = NRChannel(cell)
        corrected = channel.frequency_offset(values, -real_value("known_frequency_offset_hz",known_frequency_offset_hz),
                                             -real_value("known_initial_phase_rad",known_initial_phase_rad))
        trace.record("rx.cfo_corrected",corrected,title="Known CFO / initial phase removed")
        corrected = channel.timing_advance(corrected, known_delay_samples)
        trace.record("rx.timing_corrected",corrected,title="Known delay corrected, zero-filled boundaries")
        grid = NROFDM(cell, self.carrier_frequency_hz).demodulate(corrected, cp_fraction,plotter=trace)
        indices = self.resource.indices()
        received = grid[:,indices[:,1],indices[:,2]].reshape(cell.n_rx_antennas,self.resource.n_symbols,12)
        trace.record("rx.extracted_symbols",received.reshape(cell.n_rx_antennas,-1),kind="sequence",title="Received PUCCH REs; frequency then symbol",xlabel="PUCCH RE index")
        energy = float(np.sum(np.abs(received)**2))
        candidates = []
        correlations = []
        for bits, sr in self._hypotheses():
            reference = self.resource.generate(bits,sr).reshape(self.resource.n_symbols,12)
            projection = np.sum(received*reference.conj()[None,:,:],axis=2)
            correlations.append(projection/12)  # 单位能量参考归一化，得到每Rx/符号的复相关输出。
            # 每符号12点序列能量=12；逐Rx/符号非相干功率和对总资源能量归一化。
            metric = float(np.clip(np.sum(np.abs(projection)**2)/(12*energy),0,1)) if energy > 0 else 0.0
            candidates.append({"harq_ack":list(bits), "sr":sr,
                               "m_cs":self.resource.cyclic_shift_offset(bits,sr), "metric":metric})
        best = max(candidates,key=lambda x:x["metric"])
        detected = energy > 0 and best["metric"] > self.detection_threshold
        candidate_correlations = np.stack(correlations)  # [candidate,Rx,PUCCH symbol]
        best_correlations = candidate_correlations[candidates.index(best)].copy()
        trace.record("rx.correlated_constellation",best_correlations,kind="constellation",title=f"Normalized correlation, best m_cs={best['m_cs']} | {'detected' if detected else 'DTX: best hypothesis only'}",xlabel="I (normalized complex amplitude)",ylabel="Q (normalized complex amplitude)",labels=[f"S{s}" for s in range(self.resource.n_symbols)])
        trace.record("rx.candidate_metrics",[item["metric"] for item in candidates],kind="metric",title="Noncoherent correlation of legal UCI candidates",xlabel="Candidate m_cs",ylabel="Normalized correlation power",labels=[str(item["m_cs"]) for item in candidates])
        trace.record("rx.decision",[best["metric"],self.detection_threshold,float(detected)],kind="metric",title="Winner, threshold, and detected flag",xlabel="Decision quantity",ylabel="Dimensionless",labels=["best metric","threshold","detected"])
        if plotter is None:
            trace.show()
        return {"detected":detected, "status":"detected" if detected else "dtx",
                "harq_ack":best["harq_ack"] if detected else None,
                "sr":best["sr"] if detected else (0 if self.n_harq_ack_bits == 0 else None),
                "m_cs":best["m_cs"] if detected else None, "metric":best["metric"],
                "detection_threshold":self.detection_threshold, "candidates":candidates,
                "correlation_symbols":best_correlations,
                "candidate_correlation_symbols":candidate_correlations,
                "resource_power":energy/received.size, "rx_symbols":received.copy(), "rx_grid":grid,
                "synchronization":"explicit known-parameter correction; no blind synchronization",
                "plot_stages":list(trace.stages)}
