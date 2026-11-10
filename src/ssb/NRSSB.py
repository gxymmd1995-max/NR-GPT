"""Fixed R15 TS38.211 §7.4.2/§7.4.3: one 240-subcarrier, four-symbol SS/PBCH block."""
from dataclasses import dataclass
import numpy as np
from cell import NRCell
from grid import NRGrid
from common import NRCommon
from common.NRCommon import _integer
from common._validation import real_value

@dataclass(frozen=True,slots=True)
class NRSSB:
    cell: NRCell
    start_subcarrier: int = 0
    start_symbol: int = 2
    l_max: int = 8
    ssb_index: int = 0
    half_frame: int = 0
    k_ssb: int = 0

    def __post_init__(self):
        if not isinstance(self.cell,NRCell):
            raise TypeError('cell must be NRCell')
        if self.cell.cyclic_prefix!='normal' or self.cell.subcarrier_spacing_khz not in (15,30,120,240):
            raise ValueError('SSB requires normal CP and R15 SCS15/30/120/240')
        if (self.l_max==64)!=(self.cell.subcarrier_spacing_khz in (120,240)):
            raise ValueError('R15 Lmax64 requires FR2 SCS120/240; Lmax4/8 requires15/30')
        _integer('start_subcarrier',self.start_subcarrier,0,self.cell.n_subcarriers-240)
        _integer('start_symbol',self.start_symbol,0,self.cell.symbols_per_slot-4)
        from common.NRBCHCode import NRBCHCode
        NRBCHCode(self.cell.n_cell_id,self.l_max,self.ssb_index,self.half_frame,self.k_ssb)

    @staticmethod
    def pss(n_id_2):
        _integer('n_id_2',n_id_2,0,2)
        x=np.zeros(127,dtype=np.int8);x[:7]=[0,1,1,0,1,1,1]
        for i in range(120):
            x[i+7]=x[i+4]^x[i]
        return 1-2*x[(np.arange(127)+43*n_id_2)%127]

    @staticmethod
    def sss(cell_id):
        _integer('cell_id',cell_id,0,1007)
        x=np.zeros((2,127),dtype=np.int8);x[:,0]=1
        for i in range(120):
            x[0,i+7]=x[0,i+4]^x[0,i];x[1,i+7]=x[1,i+1]^x[1,i]
        m0=15*((cell_id//3)//112)+5*(cell_id%3);m1=(cell_id//3)%112
        return (1-2*x[0,(np.arange(127)+m0)%127])*(1-2*x[1,(np.arange(127)+m1)%127])

    def indices(self,kind='pbch'):
        if kind not in ('pss','sss','pbch','dmrs'):
            raise ValueError('kind must be pss/sss/pbch/dmrs')
        if kind in ('pss','sss'):
            coords=[(0 if kind=='pss' else 2,k) for k in range(56,183)]
        else:
            coords=[(l,k) for l in (1,2,3) for k in range(240) if (l!=2 or k<48 or k>=192) and ((k%4==self.cell.n_cell_id%4)==(kind=='dmrs'))]
        return np.array([(0,self.start_symbol+l,self.start_subcarrier+k) for l,k in coords],int)

    def dmrs(self):
        i=self.ssb_index%8
        if self.l_max==4:
            i=self.ssb_index+4*self.half_frame
        pci=self.cell.n_cell_id
        seed=(2**11*(i+1)*(pci//4+1)+2**6*(i+1)+pci%4)%2**31
        b=NRCommon.gold_sequence(seed,288).astype(int).reshape(-1,2)
        return ((1-2*b[:,0])+1j*(1-2*b[:,1]))/np.sqrt(2)

    def scrambling(self):
        v=self.ssb_index%(4 if self.l_max==4 else 8)
        return NRCommon.gold_sequence(self.cell.n_cell_id,864,offset=864*v)

    def generate(self,coded_bits):
        v=np.asarray(coded_bits)
        if v.shape!=(864,) or v.dtype.kind not in 'iu' or np.any((v!=0)&(v!=1)):
            raise ValueError('binary encoded BCH bits [864] required')
        b=(v^self.scrambling()).astype(int).reshape(-1,2)
        return ((1-2*b[:,0])+1j*(1-2*b[:,1]))/np.sqrt(2)

    def map_to_grid(self,grid,coded_bits,beta=1.):
        if not isinstance(grid,NRGrid) or grid.cell!=self.cell or grid.n_ports!=1:
            raise ValueError('matching single-port NRGrid required')
        beta=real_value('beta',beta,0)
        coords=np.concatenate([self.indices(k) for k in ('pss','sss','pbch','dmrs')])
        values=np.concatenate([self.pss(self.cell.n_id_2),self.sss(self.cell.n_cell_id),self.generate(coded_bits),self.dmrs()])
        # Reserve all 960 RE, including the standard's zero positions (table7.4.3.1-1).
        block=np.zeros((4,240),complex)
        block[coords[:,1]-self.start_symbol,coords[:,2]-self.start_subcarrier]=values
        all_coords=np.array([(0,self.start_symbol+l,self.start_subcarrier+k) for l in range(4) for k in range(240)],int)
        grid.map(all_coords,beta*block.ravel(),owner='SSB')
