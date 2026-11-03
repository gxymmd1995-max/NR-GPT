"""R15 TS38.211 §6.3.2.6, §6.4.1.3.3: one-RB F4 with frequency-domain OCC."""
from dataclasses import dataclass
import numpy as np
from cell import NRCell
from common.NRCommon import _integer
from common._validation import real_value
from grid import NRGrid
from pucch.NRPUCCH2 import NRPUCCH2
from pucch.NRPUCCH3 import NRPUCCH3


@dataclass(frozen=True,slots=True)
class NRPUCCH4:
    cell: NRCell
    prb: int = 0
    start_symbol: int = 0
    n_symbols: int = 14
    rnti: int = 1
    data_scrambling_id: int | None = None
    hopping_id: int | None = None
    group_hopping: str = 'neither'
    second_hop_prb: int | None = None
    additional_dmrs: bool = False
    modulation: str = 'QPSK'
    spreading_factor: int = 2
    occ_index: int = 0

    def __post_init__(self):
        base=self.base_resource()
        object.__setattr__(self,'data_scrambling_id',base.data_scrambling_id)
        object.__setattr__(self,'hopping_id',base.hopping_id)
        if type(self.spreading_factor) is not int or self.spreading_factor not in (2,4):raise ValueError('spreading_factor must be 2 or 4')
        _integer('occ_index',self.occ_index,0,self.spreading_factor-1)

    def base_resource(self):
        """Shared F3 geometry/DMRS base, always one RB, without F4 cyclic-shift offset."""
        return NRPUCCH3(self.cell,prb=self.prb,n_prbs=1,start_symbol=self.start_symbol,n_symbols=self.n_symbols,
            rnti=self.rnti,data_scrambling_id=self.data_scrambling_id,hopping_id=self.hopping_id,
            group_hopping=self.group_hopping,second_hop_prb=self.second_hop_prb,additional_dmrs=self.additional_dmrs,modulation=self.modulation)

    @property
    def n_prbs(self):return 1

    @property
    def dmrs_symbols(self):return self.base_resource().dmrs_symbols

    @property
    def data_symbols(self):return self.base_resource().data_symbols

    @property
    def coded_length(self):return self.base_resource().coded_length//self.spreading_factor

    def indices(self,dmrs=False):return self.base_resource().indices(dmrs)

    def scrambling(self):
        from common import NRCommon
        return NRCommon.gold_sequence(self.rnti*2**15+self.data_scrambling_id,self.coded_length)

    def occ(self):
        """Table 6.3.2.6.3-1/-2, expanded to 12 entries. Unscaled unit-modulus OCC."""
        # The R15 table uses [1,-j,-1,+j] for SF4 index1 (negative exponent).
        rows=([1,1],[1,-1]) if self.spreading_factor==2 else (
            [1,1,1,1],[1,-1j,-1,1j],[1,-1,1,-1],[1,1j,-1,-1j])
        return np.repeat(np.asarray(rows[self.occ_index],dtype=complex),12//self.spreading_factor)

    def spread(self,symbols):
        """Input [data_symbols,12/SF], output [data_symbols,12], no 1/sqrt(SF) scaling."""
        values=np.asarray(symbols,dtype=complex)
        if values.shape!=(len(self.data_symbols),12//self.spreading_factor) or not np.all(np.isfinite(values)):raise ValueError('finite modulation symbols [S,12/SF] required')
        return np.tile(values,(1,self.spreading_factor))*self.occ()[None,:]

    def despread(self,symbols):
        """Conjugate-OCC combine after 12-point IDFT, divided by SF; input [S,12]."""
        values=np.asarray(symbols,dtype=complex)
        if values.shape!=(len(self.data_symbols),12) or not np.all(np.isfinite(values)):raise ValueError('finite IDFT symbols [S,12] required')
        return (values*self.occ().conj()[None,:]).reshape(len(self.data_symbols),self.spreading_factor,12//self.spreading_factor).mean(axis=1)

    def generate(self,coded_bits):
        v=np.asarray(coded_bits)
        if v.shape!=(self.coded_length,) or v.dtype.kind not in 'iu' or np.any((v!=0)&(v!=1)):raise ValueError('binary coded bits [E] required')
        scrambled=v^self.scrambling()
        d=NRPUCCH2.qpsk(scrambled) if self.modulation=='QPSK' else (1-2*scrambled.astype(int))*(1+1j)/np.sqrt(2)*np.exp(1j*np.pi/2*(np.arange(len(scrambled))%2))
        spread=self.spread(d.reshape(len(self.data_symbols),12//self.spreading_factor))
        return np.fft.fft(spread,axis=-1,norm='ortho').ravel()

    def dmrs(self):
        # Table 6.4.1.3.3.1-1; m0 differs from OCC's block phase index.
        m0=(0,6)[self.occ_index] if self.spreading_factor==2 else (0,6,3,9)[self.occ_index]
        base=self.base_resource().dmrs().reshape(-1,12)
        return (base*np.exp(2j*np.pi*m0*np.arange(12)/12)[None,:]).ravel()

    def map_to_grid(self,grid,coded_bits,beta=1.):
        if not isinstance(grid,NRGrid) or grid.cell!=self.cell or grid.n_ports!=1:raise ValueError('matching one-port grid required')
        amplitude=real_value('beta',beta,0)
        indices=np.concatenate([self.indices(),self.indices(True)])
        grid.map(indices,amplitude*np.concatenate([self.generate(coded_bits),self.dmrs()]),owner='PUCCH')
        return len(indices)
