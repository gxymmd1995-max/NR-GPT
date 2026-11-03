"""R15 TS38.211 V15.2.0 §6.3.2.4、§6.4.1.3.1：F1数据/DMRS和时域OCC。"""
from dataclasses import dataclass
import numpy as np
from cell import NRCell
from common import NRCommon
from common.NRCommon import _integer
from common._validation import real_value
from grid import NRGrid


@dataclass(frozen=True, slots=True)
class NRPUCCH1:
    cell: NRCell
    prb: int = 0
    start_symbol: int = 0
    n_symbols: int = 14
    initial_cyclic_shift: int = 0
    hopping_id: int | None = None
    group_hopping: str = 'neither'
    second_hop_prb: int | None = None
    time_domain_occ: int = 0

    def __post_init__(self):
        if not isinstance(self.cell, NRCell):
            raise TypeError('cell must be NRCell')
        _integer('n_symbols', self.n_symbols, 4, self.cell.symbols_per_slot)
        _integer('start_symbol', self.start_symbol, 0, self.cell.symbols_per_slot-self.n_symbols)
        _integer('prb', self.prb, 0, self.cell.bwp_size-1)
        _integer('initial_cyclic_shift', self.initial_cyclic_shift, 0, 11)
        if self.hopping_id is None:
            object.__setattr__(self, 'hopping_id', self.cell.n_cell_id)
        _integer('hopping_id', self.hopping_id, 0, 1023)
        if self.group_hopping not in ('neither', 'enable'):
            raise ValueError('F1 supports neither or enable group hopping')
        if self.second_hop_prb is not None:
            _integer('second_hop_prb', self.second_hop_prb, 0, self.cell.bwp_size-1)
        counts = [len(np.flatnonzero((self.hops == h) & (np.arange(self.n_symbols)%2 == p)))
                  for h in np.unique(self.hops) for p in (0, 1)]
        _integer('time_domain_occ', self.time_domain_occ, 0, min(counts)-1)

    @property
    def hops(self):
        """每资源符号的跳号[L]，第二跳从floor(L/2)开始；同PRB也视为启用跳频。"""
        return (np.arange(self.n_symbols) >= self.n_symbols//2).astype(int) if self.second_hop_prb is not None else np.zeros(self.n_symbols, int)

    @staticmethod
    def modulate(bits):
        """§5.1 BPSK/QPSK，输入1/2个整数位，返回单位能量复标量。"""
        values = tuple(bits)
        if len(values) not in (1, 2) or any(type(b) not in (int, np.int64, np.int32) or b not in (0, 1) for b in values):
            raise ValueError('bits must contain one or two integer bits')
        return ((1-2*values[0])+1j*(1-2*values[-1]))/np.sqrt(2)

    def reference(self):
        """返回含逐符号循环移位与OCC的单位模参考[L,12]；数据与DMRS独立计数。"""
        out = []
        parity = np.arange(self.n_symbols)%2
        for l in range(self.n_symbols):
            hop = int(self.hops[l])
            group = self.hopping_id%30
            if self.group_hopping == 'enable':
                bits = NRCommon.gold_sequence(self.hopping_id//30, 8, offset=8*(2*self.cell.n_slot+hop))
                group = (group+int(bits @ (2**np.arange(8))))%30
            params = NRCommon.pucch_sequence_parameters(self.hopping_id, self.cell.n_slot,
                self.start_symbol+l, 1, self.initial_cyclic_shift, symbols_per_slot=self.cell.symbols_per_slot)
            positions = np.flatnonzero((self.hops == hop) & (parity == parity[l]))
            m = int(np.flatnonzero(positions == l)[0]); size = len(positions)
            # Table 6.3.2.4.1-2: N=4 uses Walsh ordering, not a DFT matrix.
            phase = ([ [0,0,0,0], [0,2,0,2], [0,0,2,2], [0,2,2,0] ][self.time_domain_occ][m]
                     if size == 4 else self.time_domain_occ*m%size)
            out.append(NRCommon.low_papr_sequence_12(group, int(params['cyclic_shift'][0]))*np.exp(2j*np.pi*phase/size))
        return np.array(out)

    def generate(self, bits):
        """全部资源符号[L,12]，偶数相对符号DMRS，奇数相对符号数据。"""
        result = self.reference()
        result[1::2] *= self.modulate(bits)
        return result

    def indices(self):
        """零基坐标[12L,3]：逻辑端口0、slot符号、载波局部子载波。"""
        return np.array([(0, self.start_symbol+l,
            12*(self.cell.bwp_start-self.cell.n_start_grid+(self.second_hop_prb if self.hops[l] else self.prb))+n)
            for l in range(self.n_symbols) for n in range(12)], dtype=int)

    def map_to_grid(self, grid, bits, beta=1.):
        """beta非负线性幅度，数据/DMRS同幅；owner=PUCCH，返回RE数量。"""
        if not isinstance(grid, NRGrid) or grid.cell != self.cell or grid.n_ports != 1:
            raise ValueError('grid must be a matching one-port NRGrid')
        symbols = self.generate(bits)*real_value('beta', beta, 0)
        grid.map(self.indices(), symbols.ravel(), owner='PUCCH')
        return symbols.size
