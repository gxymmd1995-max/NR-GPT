"""TS38.211 V15.2.0 §6.3.2.5/§6.4.1.3.2；连续1..16RB、1/2符号F2。"""
from dataclasses import dataclass
import numpy as np
from cell import NRCell
from common import NRCommon
from common.NRCommon import _integer
from common._validation import real_value
from grid import NRGrid


@dataclass(frozen=True, slots=True)
class NRPUCCH2:
    cell: NRCell
    prb: int = 0
    n_prbs: int = 1
    start_symbol: int = 0
    n_symbols: int = 1
    rnti: int = 1
    data_scrambling_id: int | None = None
    dmrs_scrambling_id: int | None = None
    second_hop_prb: int | None = None

    def __post_init__(self):
        if not isinstance(self.cell, NRCell):
            raise TypeError('cell must be NRCell')
        _integer('n_prbs',self.n_prbs,1,min(16,self.cell.bwp_size))
        _integer('prb',self.prb,0,self.cell.bwp_size-self.n_prbs)
        _integer('n_symbols',self.n_symbols,1,2)
        _integer('start_symbol',self.start_symbol,0,self.cell.symbols_per_slot-self.n_symbols)
        _integer('rnti',self.rnti,0,65535)
        for name,maximum in [('data_scrambling_id',1023),('dmrs_scrambling_id',65535)]:
            if getattr(self,name) is None:
                object.__setattr__(self,name,self.cell.n_cell_id)
            _integer(name,getattr(self,name),0,maximum)
        if self.second_hop_prb is not None:
            _integer('second_hop_prb',self.second_hop_prb,0,self.cell.bwp_size-self.n_prbs)
            if self.n_symbols != 2:
                raise ValueError('intra-slot hopping requires two symbols')

    @property
    def coded_length(self):
        return 16*self.n_prbs*self.n_symbols

    def indices(self, dmrs=False):
        """[RE,3] port0/symbol/carrier-local k；DMRS k%3=1，其他RE为数据。"""
        if type(dmrs) is not bool:
            raise TypeError('dmrs must be bool')
        result=[]
        for s in range(self.n_symbols):
            prb=self.second_hop_prb if s==1 and self.second_hop_prb is not None else self.prb
            first=12*(self.cell.bwp_start-self.cell.n_start_grid+prb)
            result.extend((0,self.start_symbol+s,first+n) for n in range(12*self.n_prbs) if (n%3==1)==dmrs)
        return np.array(result,dtype=int)

    def scrambling(self):
        return NRCommon.gold_sequence(self.rnti*2**15+self.data_scrambling_id,self.coded_length)

    @staticmethod
    def qpsk(bits):
        v=np.asarray(bits,dtype=np.int64).reshape(-1,2)
        return ((1-2*v[:,0])+1j*(1-2*v[:,1]))/np.sqrt(2)

    def dmrs(self):
        out=[]
        for s in range(self.n_symbols):
            symbol=self.start_symbol+s
            # Fixed R15 14-symbol reference index, also when physical CP is extended.
            seed=(2**17*(14*self.cell.n_slot+symbol+1)*(2*self.dmrs_scrambling_id+1)+2*self.dmrs_scrambling_id)%2**31
            prb=self.second_hop_prb if s==1 and self.second_hop_prb is not None else self.prb
            crb=self.cell.bwp_start+prb
            bits=NRCommon.gold_sequence(seed,8*self.n_prbs,offset=8*crb)
            out.extend(self.qpsk(bits))
        return np.array(out)

    def generate(self, coded_bits):
        values=tuple(coded_bits)
        if len(values)!=self.coded_length or any(isinstance(b,(bool,np.bool_)) or not isinstance(b,(int,np.integer)) or b not in (0,1) for b in values):
            raise ValueError('coded_bits must contain exactly coded_length binary integers')
        return self.qpsk(np.asarray(values)^self.scrambling())

    def map_to_grid(self,grid,coded_bits,beta=1.):
        if not isinstance(grid,NRGrid) or grid.cell!=self.cell or grid.n_ports!=1:
            raise ValueError('matching single-port NRGrid required')
        amplitude=real_value('beta',beta,0)
        data=self.generate(coded_bits); pilot=self.dmrs()
        indices=np.concatenate([self.indices(),self.indices(True)])
        grid.map(indices,amplitude*np.concatenate([data,pilot]),owner='PUCCH')
        return len(indices)
