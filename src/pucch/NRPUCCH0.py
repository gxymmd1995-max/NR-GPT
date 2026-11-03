"""PUCCH Format 0资源/序列；TS38.211 V15.2.0与TS38.213 V15.3.0固定基线。"""

from dataclasses import dataclass

import numpy as np

from cell import NRCell
from common import NRCommon
from common.NRCommon import _integer
from common._validation import real_value
from grid import NRGrid


def _harq_ack(bits) -> tuple[int, ...]:
    """按传输顺序解释0..2个HARQ-ACK比特；0=NACK，1=ACK，不反转位序。"""
    values = np.asarray(bits)
    if values.ndim != 1 or values.size > 2:
        raise ValueError("harq_ack must be a one-dimensional sequence of 0..2 bits")
    contains_bool = any(isinstance(x, (bool, np.bool_)) for x in np.asarray(bits, dtype=object).flat)
    if values.size and (contains_bool or values.dtype.kind not in "iu" or np.any((values != 0) & (values != 1))):
        raise ValueError("harq_ack must contain integer 0/1 bits, not bool or float")
    return tuple(int(x) for x in values)


@dataclass(frozen=True, slots=True)
class NRPUCCH0:
    """单slot、单RB、端口2000的F0配置；PRB号相对活动BWP，非CRB。"""

    cell: NRCell
    prb: int = 0
    start_symbol: int | None = None  # None取当前CP类型slot的最后一个符号。
    n_symbols: int = 1
    initial_cyclic_shift: int = 0
    hopping_id: int | None = None  # None回退PCI；显式ID为10bit。
    group_hopping: str = "neither"
    second_hop_prb: int | None = None  # None不跳频；非None只支持2符号时隙内跳频。

    def __post_init__(self):
        """校验F0资源完全位于当前slot与BWP内；不代替TDD调度/资源指示器过程。"""
        if not isinstance(self.cell, NRCell):
            raise TypeError("cell must be NRCell")
        _integer("n_symbols", self.n_symbols, 1, 2)
        if self.start_symbol is None:
            object.__setattr__(self, "start_symbol", self.cell.symbols_per_slot-self.n_symbols)
        _integer("start_symbol", self.start_symbol, 0, self.cell.symbols_per_slot-self.n_symbols)
        _integer("prb", self.prb, 0, self.cell.bwp_size-1)
        _integer("initial_cyclic_shift", self.initial_cyclic_shift, 0, 11)
        if self.hopping_id is None:
            object.__setattr__(self, "hopping_id", self.cell.n_cell_id)
        _integer("hopping_id", self.hopping_id, 0, 1023)
        if self.group_hopping not in ("neither", "enable"):
            raise ValueError("F0 supports neither/enable; sequence hopping disable can require undefined v=1 for 12-point sequences")
        if self.second_hop_prb is not None:
            _integer("second_hop_prb", self.second_hop_prb, 0, self.cell.bwp_size-1)
            if self.n_symbols != 2:
                raise ValueError("F0 intra-slot hopping requires two symbols")

    @staticmethod
    def cyclic_shift_offset(harq_ack=(), sr: int | None = None) -> int | None:
        """38.213 V15.3.0表9.2.3-3/-4及9.2.5-1/-2；SR-only负SR返回None=DTX。"""
        bits = _harq_ack(harq_ack)
        if sr is not None:
            _integer("sr", sr, 0, 1)
        if not bits:
            if sr is None:
                raise ValueError("at least one HARQ-ACK bit or an SR occasion is required")
            return 0 if sr else None
        if len(bits) == 1:
            return 6*bits[0]+(3 if sr == 1 else 0)
        # 原表按00,01,11,10列出；不能把输入位序当普通二进制0,1,2,3乘3。
        base = {(0,0):0, (0,1):3, (1,1):6, (1,0):9}[bits]
        return base+(1 if sr == 1 else 0)

    def sequence_parameters(self, m_cs: int = 0) -> dict[str, np.ndarray]:
        """每项[n_symbols]；u/v、n_cs、mod12移位和rad相位，公用PUCCH专用Gold规则。"""
        return NRCommon.pucch_sequence_parameters(
            self.hopping_id, self.cell.n_slot, self.start_symbol, self.n_symbols,
            self.initial_cyclic_shift, m_cs, self.group_hopping,
            self.second_hop_prb is not None, self.cell.symbols_per_slot)

    def generate(self, harq_ack=(), sr: int | None = None) -> np.ndarray:
        """未施加beta的complex128[12*n_symbols]；先频率后符号，SR-only负SR为[0]。"""
        offset = self.cyclic_shift_offset(harq_ack, sr)
        if offset is None:
            return np.empty(0, dtype=complex)
        parameters = self.sequence_parameters(offset)
        return np.concatenate([NRCommon.low_papr_sequence_12(int(u), int(shift))
                               for u, shift in zip(parameters["u"], parameters["cyclic_shift"])])

    def indices(self) -> np.ndarray:
        """配置资源的零基[N_RE,3]坐标[逻辑端口0,slot符号,载波局部k]，与UCI/DTX无关。"""
        indices = []
        for symbol in range(self.n_symbols):
            prb = self.second_hop_prb if symbol == 1 and self.second_hop_prb is not None else self.prb
            first = 12*(self.cell.bwp_start-self.cell.n_start_grid+prb)
            indices.extend((0,self.start_symbol+symbol,first+k) for k in range(12))
        return np.asarray(indices, dtype=np.int64)

    def map_to_grid(self, grid: NRGrid, harq_ack=(), sr: int | None = None,
                    beta: float = 1.0) -> int:
        """原子写入owner=PUCCH；beta为非负线性幅度；返回实际写入RE数，DTX为0且不占用。"""
        if not isinstance(grid, NRGrid) or grid.cell != self.cell or grid.n_ports != 1:
            raise ValueError("grid must be a one-port NRGrid with the same cell")
        amplitude = real_value("beta", beta, 0)
        symbols = self.generate(harq_ack, sr)
        if symbols.size:
            grid.map(self.indices(), amplitude*symbols, owner="PUCCH")
        return int(symbols.size)

    def to_dict(self) -> dict:
        """JSON可保存的已规范化配置；hopping_id和start_symbol均已解析，端口固定2000。"""
        return {"cell":self.cell.to_dict(), "prb":self.prb, "start_symbol":self.start_symbol,
                "n_symbols":self.n_symbols, "initial_cyclic_shift":self.initial_cyclic_shift,
                "hopping_id":self.hopping_id, "group_hopping":self.group_hopping,
                "second_hop_prb":self.second_hop_prb, "antenna_port":2000}
