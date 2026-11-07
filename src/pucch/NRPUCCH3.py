"""R15 TS38.211 §6.3.2.6/§6.4.1.3.3: F3 DFT-s-OFDM, QPSK/pi2-BPSK."""
from dataclasses import dataclass
from pathlib import Path
from math import isqrt
import json
import numpy as np
from cell import NRCell
from common import NRCommon
from common.NRCommon import _integer
from common._validation import real_value
from grid import NRGrid
from pucch.NRPUCCH2 import NRPUCCH2


@dataclass(frozen=True,slots=True)
class NRPUCCH3:
    cell: NRCell
    prb: int = 0
    n_prbs: int = 1
    start_symbol: int = 0
    n_symbols: int = 14
    rnti: int = 1
    data_scrambling_id: int | None = None
    hopping_id: int | None = None
    group_hopping: str = 'neither'
    second_hop_prb: int | None = None
    additional_dmrs: bool = False
    modulation: str = 'QPSK'

    def __post_init__(self):
        if not isinstance(self.cell,NRCell):
            raise TypeError('cell must be NRCell')
        _integer('n_symbols',self.n_symbols,4,self.cell.symbols_per_slot)
        _integer('start_symbol',self.start_symbol,0,self.cell.symbols_per_slot-self.n_symbols)
        if self.n_prbs not in (1,2,3,4,5,6,8,9,10,12,15,16) or type(self.n_prbs) is not int:
            raise ValueError('invalid DFT bandwidth')
        _integer('prb',self.prb,0,self.cell.bwp_size-self.n_prbs)
        if self.second_hop_prb is not None:
            _integer('second_hop_prb',self.second_hop_prb,0,self.cell.bwp_size-self.n_prbs)
        _integer('rnti',self.rnti,0,65535)
        for name in ('data_scrambling_id','hopping_id'):
            if getattr(self,name) is None:
                object.__setattr__(self,name,self.cell.n_cell_id)
            _integer(name,getattr(self,name),0,1023)
        if type(self.additional_dmrs) is not bool:
            raise TypeError('additional_dmrs must be bool')
        if self.modulation not in ('QPSK','pi/2-BPSK'):
            raise ValueError('invalid modulation')
        if self.group_hopping not in ('neither','enable','disable'):
            raise ValueError('invalid group hopping')

    @property
    def dmrs_symbols(self):
        # Table 6.4.1.3.3.2-1, relative symbols; 4-symbol allocation has a hopping exception.
        L=self.n_symbols
        if L==4:
            return np.array([0,2] if self.second_hop_prb is not None else [1])
        if self.additional_dmrs and L>=10:
            return np.array({10:[1,3,6,8],11:[1,3,6,9],12:[1,4,7,10],13:[1,4,7,11],14:[1,5,8,12]}[L])
        return np.array({5:[0,3],6:[1,4],7:[1,4],8:[1,5],9:[1,6],10:[2,7],11:[2,7],12:[2,8],13:[2,9],14:[3,10]}[L])

    @property
    def data_symbols(self):
        return np.array([s for s in range(self.n_symbols) if s not in self.dmrs_symbols])

    @property
    def coded_length(self):
        return len(self.data_symbols)*12*self.n_prbs*(2 if self.modulation=='QPSK' else 1)

    def indices(self,dmrs=False):
        if type(dmrs) is not bool:
            raise TypeError('dmrs must be bool')
        symbols=self.dmrs_symbols if dmrs else self.data_symbols
        return np.array([(0,self.start_symbol+int(s),
            12*(self.cell.bwp_start-self.cell.n_start_grid+(self.second_hop_prb if self.second_hop_prb is not None and s>=self.n_symbols//2 else self.prb))+n)
            for s in symbols for n in range(12*self.n_prbs)],dtype=int)

    def scrambling(self):
        return NRCommon.gold_sequence(self.rnti*2**15+self.data_scrambling_id,self.coded_length)

    def generate(self,coded_bits):
        v=np.asarray(coded_bits)
        if v.shape!=(self.coded_length,) or v.dtype.kind not in 'iu' or np.any((v!=0)&(v!=1)):
            raise ValueError('binary encoded [E] required')
        scrambled=v^self.scrambling()
        d=NRPUCCH2.qpsk(scrambled) if self.modulation=='QPSK' else (1-2*scrambled.astype(int))*(1+1j)/np.sqrt(2)*np.exp(1j*np.pi/2*(np.arange(len(scrambled))%2))
        return np.fft.fft(d.reshape(-1,12*self.n_prbs),axis=-1,norm='ortho').ravel()

    def dmrs(self):
        out=[];M=12*self.n_prbs;n=np.arange(M)
        for symbol in self.dmrs_symbols:
            hop=int(self.second_hop_prb is not None and symbol>=self.n_symbols//2)
            u=self.hopping_id%30;v=0;t=2*self.cell.n_slot+hop
            if self.group_hopping=='enable':
                u=(u+int(NRCommon.gold_sequence(self.hopping_id//30,8,offset=8*t)@(2**np.arange(8))))%30
            elif self.group_hopping=='disable' and M>=72:
                v=int(NRCommon.gold_sequence(32*(self.hopping_id//30)+self.hopping_id%30,1,offset=t)[0])
            params=NRCommon.pucch_sequence_parameters(self.hopping_id,self.cell.n_slot,self.start_symbol+int(symbol),1,symbols_per_slot=self.cell.symbols_per_slot)
            alpha=params['alpha'][0]
            if M==12:
                base=NRCommon.low_papr_sequence_12(u)
            elif M==24:
                base=np.exp(1j*np.pi/4*np.array(json.loads(Path(__file__).parents[1].joinpath('common/_low_papr_24.json').read_text())[u]))
            else:
                prime=M-1
                while any(prime%d==0 for d in range(2,isqrt(prime)+1)):
                    prime-=1
                qbar=prime*(u+1)/31;q=int(np.floor(qbar+.5))+v*(-1)**int(np.floor(2*qbar));m=n%prime
                base=np.exp(-1j*np.pi*((q*m*(m+1))%(2*prime))/prime)
            out.extend(base*np.exp(1j*alpha*n))
        return np.array(out)

    def map_to_grid(self,grid,coded_bits,beta=1.):
        if not isinstance(grid,NRGrid) or grid.cell!=self.cell or grid.n_ports!=1:
            raise ValueError('matching one-port grid required')
        amplitude=real_value('beta',beta,0)
        indices=np.concatenate([self.indices(),self.indices(True)])
        grid.map(indices,amplitude*np.concatenate([self.generate(coded_bits),self.dmrs()]),owner='PUCCH')
        return len(indices)
