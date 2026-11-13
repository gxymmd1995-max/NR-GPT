"""PUCCH F0发送链：UCI→循环移位序列→NRGrid→NR OFDM单slot时域波形。"""

from dataclasses import dataclass

import numpy as np

from common import NROFDM, NRCommon
from grid import NRGrid
from diagnostics import NRPlotConfig, NRStagePlotter
from pucch.NRPUCCH0 import NRPUCCH0


@dataclass(frozen=True, slots=True)
class NRPUCCH0Transmitter:
    """一次发送一个端口2000的F0资源；物理天线预编码由外部信道/空间映射提供。"""

    resource: NRPUCCH0
    carrier_frequency_hz: float = 0.0
    plot_config: NRPlotConfig | None = None

    def __post_init__(self):
        if not isinstance(self.resource, NRPUCCH0):
            raise TypeError("resource must be NRPUCCH0")
        NROFDM(self.resource.cell, self.carrier_frequency_hz)
        NRStagePlotter(self.plot_config)

    def transmit(
        self, harq_ack=(), sr: int | None = None, beta: float = 1.0, *, plotter=None
    ) -> dict:
        """输入0..2个HARQ位及可选SR，输出完整单slot波形[1,T]及发送诊断数据。

        负SR-only输出全零波形、无占用网格，不假造负SR参考。beta含义见resource.map_to_grid。
        """
        trace = NRStagePlotter(self.plot_config) if plotter is None else plotter
        symbols = self.resource.generate(harq_ack, sr)
        shift = self.resource.cyclic_shift_offset(harq_ack, sr)
        if trace.config.enabled:
            trace.record(
                "tx.uci_shift",
                [] if shift is None else [shift],
                kind="metric",
                title="HARQ/SR -> m_cs; empty means DTX",
                xlabel="UCI candidate",
                ylabel="Cyclic-shift offset",
            )
            if shift is not None:
                params = self.resource.sequence_parameters(shift)
                base = np.array(
                    [NRCommon.low_papr_sequence_12(int(u)) for u in params["u"]]
                )
                trace.record(
                    "tx.base_sequence",
                    base,
                    kind="sequence",
                    title="Diagnostic base sequences: same u, zero cyclic shift",
                    xlabel="Sequence point",
                )
                trace.record(
                    "tx.cyclic_shift",
                    symbols.reshape(self.resource.n_symbols, 12),
                    kind="sequence",
                    title="Actual cyclic-shifted sequences, one branch per symbol",
                    xlabel="Sequence point",
                )
                trace.record(
                    "tx.alpha",
                    params["alpha"],
                    kind="metric",
                    title="Cyclic-shift phase step per PUCCH symbol",
                    xlabel="PUCCH symbol",
                    ylabel="Phase step (rad / point)",
                )
        grid = NRGrid(self.resource.cell, 1)
        count = self.resource.map_to_grid(grid, harq_ack, sr, beta)
        if trace.config.enabled:
            trace.record(
                "tx.mapped_grid",
                grid.data,
                kind="grid",
                title="Actual beta-scaled PUCCH resource grid",
                xlabel="Slot symbol",
                ylabel="Carrier-local subcarrier",
            )
        waveform = NROFDM(self.resource.cell, self.carrier_frequency_hz).modulate(
            grid.data, plotter=trace
        )
        if plotter is None:
            trace.show()
        return {
            "waveform": waveform,
            "grid": grid,
            "symbols": symbols,
            "indices": self.resource.indices(),
            "n_mapped_re": count,
            "m_cs": shift,
            "active": count > 0,
            "plot_stages": list(trace.stages),
        }
