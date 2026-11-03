"""R15 TS38.211 §6.3.1/§6.4.1.1: single-layer CP-OFDM PUSCH, type-A single DMRS."""
from dataclasses import dataclass
import numpy as np
from cell import NRCell
from common import NRCommon
from common.NRCommon import _integer
from common._validation import real_value
from grid import NRGrid


@dataclass(frozen=True,slots=True)
class NRPUSCH:
    cell: NRCell
    prb: int = 0
    n_prbs: int = 4
    start_symbol: int = 0
    n_symbols: int = 14
    rnti: int = 1
    data_scrambling_id: int | None = None
    dmrs_scrambling_id: int | None = None
    n_scid: int = 0
    dmrs_type_a_position: int = 2
    cdm_groups_without_data: int = 1
    modulation: str = 'QPSK'

    def __post_init__(self):
        if not isinstance(self.cell,NRCell):raise TypeError('cell must be NRCell')
        _integer('n_prbs',self.n_prbs,1,self.cell.bwp_size)
        _integer('prb',self.prb,0,self.cell.bwp_size-self.n_prbs)
        _integer('n_symbols',self.n_symbols,4,self.cell.symbols_per_slot)
        _integer('start_symbol',self.start_symbol,0,min(3,self.cell.symbols_per_slot-self.n_symbols))
        _integer('dmrs_type_a_position',self.dmrs_type_a_position,2,3)
        if not self.start_symbol<=self.dmrs_type_a_position<self.start_symbol+self.n_symbols:raise ValueError('allocation must contain type-A DMRS symbol')
        _integer('rnti',self.rnti,0,65535);_integer('n_scid',self.n_scid,0,1)
        _integer('cdm_groups_without_data',self.cdm_groups_without_data,1,2)
        for name,maximum in [('data_scrambling_id',1023),('dmrs_scrambling_id',65535)]:
            if getattr(self,name) is None:object.__setattr__(self,name,self.cell.n_cell_id)
            _integer(name,getattr(self,name),0,maximum)
        if self.modulation not in ('QPSK','16QAM','64QAM','256QAM'):raise ValueError('invalid modulation')

    @property
    def modulation_order(self):return dict(QPSK=2,**{'16QAM':4,'64QAM':6,'256QAM':8})[self.modulation]

    @property
    def coded_length(self):return len(self.indices())*self.modulation_order

    def indices(self,dmrs=False):
        if type(dmrs) is not bool:raise TypeError('dmrs must be bool')
        first=12*(self.cell.bwp_start-self.cell.n_start_grid+self.prb)
        result=[]
        for symbol in range(self.start_symbol,self.start_symbol+self.n_symbols):
            for n in range(12*self.n_prbs):
                is_pilot=symbol==self.dmrs_type_a_position and n%2==0
                is_reserved=symbol==self.dmrs_type_a_position and self.cdm_groups_without_data==2
                if (dmrs and is_pilot) or (not dmrs and not is_pilot and not is_reserved):result.append((0,symbol,first+n))
        return np.array(result,dtype=int)

    def scrambling(self):return NRCommon.gold_sequence(self.rnti*2**15+self.data_scrambling_id,self.coded_length)

    def constellation(self):
        qm=self.modulation_order
        labels=((np.arange(2**qm)[:,None]>>np.arange(qm-1,-1,-1))&1).astype(np.int8)
        axes=[]
        for parity in (0,1):
            axis=labels[:,parity::2];amplitude=1-2*axis[:,-1].astype(int)
            for j in range(axis.shape[1]-2,-1,-1):amplitude=(1-2*axis[:,j])*(2**(axis.shape[1]-1-j)-amplitude)
            axes.append(amplitude)
        return (axes[0]+1j*axes[1])/np.sqrt(2/3*(2**qm-1)),labels

    def generate(self,coded_bits):
        v=np.asarray(coded_bits)
        if v.shape!=(self.coded_length,) or v.dtype.kind not in 'iu' or np.any((v!=0)&(v!=1)):raise ValueError('binary coded bits [G] required')
        scrambled=(v^self.scrambling()).reshape(-1,self.modulation_order)
        index=scrambled@(2**np.arange(self.modulation_order-1,-1,-1))
        return self.constellation()[0][index]

    def dmrs(self):
        nid=self.dmrs_scrambling_id
        seed=(2**17*(self.cell.symbols_per_slot*self.cell.n_slot+self.dmrs_type_a_position+1)*(2*nid+1)+2*nid+self.n_scid)%2**31
        crb=self.cell.bwp_start+self.prb
        bits=NRCommon.gold_sequence(seed,12*self.n_prbs,offset=12*crb).astype(int).reshape(-1,2)
        return ((1-2*bits[:,0])+1j*(1-2*bits[:,1]))/np.sqrt(2)

    def map_to_grid(self,grid,coded_bits,beta=1.):
        if not isinstance(grid,NRGrid) or grid.cell!=self.cell or grid.n_ports!=1:raise ValueError('matching one-port grid required')
        amplitude=real_value('beta',beta,0);indices=np.concatenate([self.indices(),self.indices(True)])
        grid.map(indices,amplitude*np.concatenate([self.generate(coded_bits),self.dmrs()]),owner='PUSCH')
        return len(indices)
