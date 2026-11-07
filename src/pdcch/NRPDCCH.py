"""Fixed TS38.211 V15.2.0 §7.3.2/§7.4.1.3, one explicitly selected candidate."""
from dataclasses import dataclass
import numpy as np
from cell import NRCell
from grid import NRGrid
from common import NRCommon
from common.NRCommon import _integer
from common._validation import real_value

@dataclass(frozen=True,slots=True)
class NRPDCCH:
    cell: NRCell
    frequency_resources: tuple[int,...] = (0,1)
    duration: int = 2
    start_symbol: int = 0
    aggregation_level: int = 1
    cce_start: int = 0
    mapping_type: str = 'noninterleaved'
    reg_bundle_size: int = 6
    interleaver_size: int = 2
    shift_index: int = 0
    scrambling_id: int = 1
    scrambling_rnti: int = 1
    dmrs_reference_rb: int = 0
    dmrs_type_a_position: int = 2

    def __post_init__(self):
        if not isinstance(self.cell,NRCell):
            raise TypeError('cell must be NRCell')
        if self.cell.bwp_start%6:
            raise ValueError('first version requires six-CRB-aligned BWP start')
        if not isinstance(self.frequency_resources,tuple) or not self.frequency_resources or tuple(sorted(set(self.frequency_resources)))!=self.frequency_resources:
            raise ValueError('frequency_resources must be sorted unique six-RB group indices')
        for group in self.frequency_resources:
            _integer('frequency group',group,0,44)
        if 6*(self.frequency_resources[-1]+1)>self.cell.bwp_size:
            raise ValueError('CORESET exceeds BWP')
        _integer('duration',self.duration,1,3)
        _integer('dmrs_type_a_position',self.dmrs_type_a_position,2,3)
        if self.duration==3 and self.dmrs_type_a_position!=3:
            raise ValueError('R15 duration3 requires type-A position3')
        _integer('start_symbol',self.start_symbol,0,self.cell.symbols_per_slot-self.duration)
        if type(self.aggregation_level) is not int or self.aggregation_level not in (1,2,4,8,16):
            raise ValueError('invalid aggregation level')
        _integer('cce_start',self.cce_start,0,self.n_cce-self.aggregation_level)
        if self.cce_start%self.aggregation_level:
            raise ValueError('candidate CCE start must align to aggregation level')
        if self.mapping_type not in ('interleaved','noninterleaved'):
            raise ValueError('invalid mapping type')
        allowed=(2,6) if self.duration==1 else (self.duration,6)
        if self.reg_bundle_size not in allowed or type(self.reg_bundle_size) is not int:
            raise ValueError('invalid REG bundle size')
        if self.interleaver_size not in (2,3,6) or type(self.interleaver_size) is not int:
            raise ValueError('invalid interleaver size')
        if self.mapping_type=='interleaved' and self.n_regs%(self.reg_bundle_size*self.interleaver_size):
            raise ValueError('noninteger REG interleaver columns')
        _integer('shift_index',self.shift_index,0,274)
        _integer('scrambling_id',self.scrambling_id,0,65535)
        _integer('scrambling_rnti',self.scrambling_rnti,0,65535)
        _integer('dmrs_reference_rb',self.dmrs_reference_rb,0,self.cell.bwp_start+6*self.frequency_resources[0])

    @property
    def n_regs(self):
        return 6*len(self.frequency_resources)*self.duration

    @property
    def n_cce(self):
        return self.n_regs//6

    @property
    def coded_length(self):
        return 108*self.aggregation_level

    def regs(self):
        # REG numbering time-first. Return sorted physical (symbol, carrier-local RB).
        regs=[];L=6 if self.mapping_type=='noninterleaved' else self.reg_bundle_size
        total=self.n_regs//L;R=self.interleaver_size;C=total//R
        rbs=[6*g+i for g in self.frequency_resources for i in range(6)]
        for cce in range(self.cce_start,self.cce_start+self.aggregation_level):
            for bundle in range(6*cce//L,6*(cce+1)//L):
                mapped=bundle if self.mapping_type=='noninterleaved' else ((bundle%R)*C+bundle//R+self.shift_index)%total
                for reg in range(mapped*L,(mapped+1)*L):
                    rb=rbs[reg//self.duration]+self.cell.bwp_start-self.cell.n_start_grid
                    regs.append((self.start_symbol+reg%self.duration,rb))
        return sorted(regs)

    def indices(self,dmrs=False):
        if type(dmrs) is not bool:
            raise TypeError('dmrs must be bool')
        return np.array([(0,l,12*rb+k) for l,rb in self.regs() for k in range(12) if (k%4==1)==dmrs],int)

    def scrambling(self):
        return NRCommon.gold_sequence((self.scrambling_rnti*2**16+self.scrambling_id)%2**31,self.coded_length)

    def generate(self,bits):
        v=np.asarray(bits)
        if v.shape!=(self.coded_length,) or v.dtype.kind not in 'iu' or np.any((v!=0)&(v!=1)):
            raise ValueError('binary rate-matched bits [E] required')
        pair=(v^self.scrambling()).reshape(-1,2)
        return ((1-2*pair[:,0].astype(int))+1j*(1-2*pair[:,1].astype(int)))/np.sqrt(2)

    def dmrs(self):
        values=[]
        for l,rb in self.regs():
            seed=(2**17*(14*self.cell.n_slot+l+1)*(2*self.scrambling_id+1)+2*self.scrambling_id)%2**31
            offset=6*(rb+self.cell.n_start_grid-self.dmrs_reference_rb)
            pair=NRCommon.gold_sequence(seed,6,offset=offset).astype(int).reshape(-1,2)
            values.extend(((1-2*pair[:,0])+1j*(1-2*pair[:,1]))/np.sqrt(2))
        return np.array(values)

    def map_to_grid(self,grid,bits,beta=1.):
        if not isinstance(grid,NRGrid) or grid.cell!=self.cell or grid.n_ports!=1:
            raise ValueError('matching single-port grid required')
        beta=real_value('beta',beta,0)
        grid.map(np.concatenate([self.indices(),self.indices(True)]),beta*np.concatenate([self.generate(bits),self.dmrs()]),owner='PDCCH')
