"""R15 TS38.211 §6.3.1/§6.4.1.1: 1..4-layer CP-OFDM PUSCH, type-A type1/2 single/double DMRS."""
from dataclasses import dataclass
import numpy as np
from cell import NRCell
from common import NRCommon
from common.NRCommon import _integer
from common._validation import real_value
from grid import NRGrid
from common._qam import constellation as qam_constellation


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
    cdm_groups_without_data: int | None = None
    modulation: str = 'QPSK'
    n_layers: int = 1
    dmrs_configuration_type: int = 1
    dmrs_length: int = 1
    dmrs_additional_position: int = 0
    dmrs_ports: tuple[int,...] | None = None

    def __post_init__(self):
        if not isinstance(self.cell,NRCell):
            raise TypeError('cell must be NRCell')
        _integer('n_prbs',self.n_prbs,1,self.cell.bwp_size)
        _integer('prb',self.prb,0,self.cell.bwp_size-self.n_prbs)
        _integer('n_symbols',self.n_symbols,4,self.cell.symbols_per_slot)
        _integer('start_symbol',self.start_symbol,0,min(3,self.cell.symbols_per_slot-self.n_symbols))
        _integer('dmrs_type_a_position',self.dmrs_type_a_position,2,3)
        if not self.start_symbol<=self.dmrs_type_a_position<self.start_symbol+self.n_symbols:
            raise ValueError('allocation must contain type-A DMRS symbol')
        _integer('rnti',self.rnti,0,65535);_integer('n_scid',self.n_scid,0,1)
        _integer('n_layers',self.n_layers,1,4)
        _integer('dmrs_configuration_type',self.dmrs_configuration_type,1,2)
        _integer('dmrs_length',self.dmrs_length,1,2)
        _integer('dmrs_additional_position',self.dmrs_additional_position,0,3 if self.dmrs_length==1 else 1)
        if self.dmrs_type_a_position==3 and self.dmrs_additional_position==3:
            raise ValueError('additional position 3 requires type-A position 2')
        if self.dmrs_ports is None:
            object.__setattr__(self,'dmrs_ports',tuple(range(self.n_layers)))
        maximum=(4 if self.dmrs_configuration_type==1 else 6)*self.dmrs_length
        if not isinstance(self.dmrs_ports,tuple) or len(self.dmrs_ports)!=self.n_layers or len(set(self.dmrs_ports))!=self.n_layers:
            raise ValueError('dmrs_ports must be a unique tuple with n_layers entries')
        for p in self.dmrs_ports:
            _integer('dmrs_port',p,0,maximum-1)
        groups=1+max(self.port_parameters(p)[0] for p in self.dmrs_ports)
        if self.cdm_groups_without_data is None:
            object.__setattr__(self,'cdm_groups_without_data',groups)
        _integer('cdm_groups_without_data',self.cdm_groups_without_data,groups,2 if self.dmrs_configuration_type==1 else 3)
        if any(l<self.start_symbol or l>=self.start_symbol+self.n_symbols for l in self.dmrs_symbols):
            raise ValueError('DMRS symbols must lie within allocation')
        for name,maximum in [('data_scrambling_id',1023),('dmrs_scrambling_id',65535)]:
            if getattr(self,name) is None:
                object.__setattr__(self,name,self.cell.n_cell_id)
            _integer(name,getattr(self,name),0,maximum)
        if self.modulation not in ('QPSK','16QAM','64QAM','256QAM'):
            raise ValueError('invalid modulation')

    @property
    def modulation_order(self):
        return dict(QPSK=2,**{'16QAM':4,'64QAM':6,'256QAM':8})[self.modulation]

    @property
    def coded_length(self):
        return len(self.indices())*self.modulation_order

    def port_parameters(self,port):
        """Tables 6.4.1.1.3-1/-2: (CDM group, frequency sign index, time sign index)."""
        single=4 if self.dmrs_configuration_type==1 else 6
        return (port%single)//2,port%2,port//single

    @property
    def dmrs_symbol_starts(self):
        """Type-A duration is allocation end relative to slot; tables 6.4.1.1.3-3/-4."""
        duration=self.start_symbol+self.n_symbols;extra=self.dmrs_additional_position
        starts=[self.dmrs_type_a_position]
        if self.dmrs_length==2:
            if extra and duration>=10:
                starts.append(8 if duration<=12 else 10)
        elif extra:
            if duration in (8,9):
                starts.append(7)
            elif duration in (10,11):
                starts += [9] if extra==1 else [6,9]
            elif duration==12:
                starts += [9] if extra==1 else [6,9] if extra==2 else [5,8,11]
            elif duration in (13,14):
                starts += [11] if extra==1 else [7,11] if extra==2 else [5,8,11]
        return np.array(starts,dtype=int)

    @property
    def dmrs_symbols(self):
        return np.array([l+t for l in self.dmrs_symbol_starts for t in range(self.dmrs_length)],dtype=int)

    def port_subcarriers(self,port):
        group,_,_=self.port_parameters(port)
        if self.dmrs_configuration_type==1:
            return np.arange(6*self.n_prbs)*2+group
        return np.array([6*n+2*group+k for n in range(2*self.n_prbs) for k in (0,1)],dtype=int)

    def indices(self,dmrs=False):
        if type(dmrs) is not bool:
            raise TypeError('dmrs must be bool')
        first=12*(self.cell.bwp_start-self.cell.n_start_grid+self.prb)
        result=[]
        for layer,port in enumerate(self.dmrs_ports):
            pilot_points=set(self.port_subcarriers(port))
            for symbol in range(self.start_symbol,self.start_symbol+self.n_symbols):
                for n in range(12*self.n_prbs):
                    group=n%2 if self.dmrs_configuration_type==1 else (n%6)//2
                    is_pilot=symbol in self.dmrs_symbols and n in pilot_points
                    reserved=symbol in self.dmrs_symbols and group<self.cdm_groups_without_data
                    if (dmrs and is_pilot) or (not dmrs and not reserved):
                        result.append((layer,symbol,first+n))
        return np.array(result,dtype=int)

    def scrambling(self):
        return NRCommon.gold_sequence(self.rnti*2**15+self.data_scrambling_id,self.coded_length)

    def constellation(self):
        return qam_constellation(self.modulation_order)

    def generate(self,coded_bits):
        v=np.asarray(coded_bits)
        if v.shape!=(self.coded_length,) or v.dtype.kind not in 'iu' or np.any((v!=0)&(v!=1)):
            raise ValueError('binary coded bits [G] required')
        scrambled=(v^self.scrambling()).reshape(-1,self.modulation_order)
        index=scrambled@(2**np.arange(self.modulation_order-1,-1,-1))
        # 38.211 table 6.3.1.3-1: round-robin codeword symbols over layers.
        return self.constellation()[0][index].reshape(-1,self.n_layers).T.ravel()

    def dmrs(self):
        nid=self.dmrs_scrambling_id;crb=self.cell.bwp_start+self.prb
        per_rb=6 if self.dmrs_configuration_type==1 else 4;result=[]
        for port in self.dmrs_ports:
            _,frequency,time=self.port_parameters(port)
            for start in self.dmrs_symbol_starts:
                for t in range(self.dmrs_length):
                    symbol=int(start+t)
                    seed=(2**17*(self.cell.symbols_per_slot*self.cell.n_slot+symbol+1)*(2*nid+1)+2*nid+self.n_scid)%2**31
                    bits=NRCommon.gold_sequence(seed,2*per_rb*self.n_prbs,offset=2*per_rb*crb).astype(int).reshape(-1,2)
                    base=((1-2*bits[:,0])+1j*(1-2*bits[:,1]))/np.sqrt(2)
                    result.extend(base*((-1)**(frequency*(np.arange(len(base))%2)+time*t)))
        return np.array(result)

    def map_to_grid(self,grid,coded_bits,beta=1.):
        if not isinstance(grid,NRGrid) or grid.cell!=self.cell or grid.n_ports!=self.n_layers:
            raise ValueError('matching n_layers-port grid required')
        amplitude=real_value('beta',beta,0);indices=np.concatenate([self.indices(),self.indices(True)])
        grid.map(indices,amplitude*np.concatenate([self.generate(coded_bits),self.dmrs()]),owner='PUSCH')
        return len(indices)
