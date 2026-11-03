"""Fixed R15 BG1/BG2 QC-LDPC; sparse GF(2) encoding, layered normalized min-sum."""
from dataclasses import dataclass
from pathlib import Path
import json
import numpy as np

LIFTING_SETS=([2,4,8,16,32,64,128,256],[3,6,12,24,48,96,192,384],
 [5,10,20,40,80,160,320],[7,14,28,56,112,224],[9,18,36,72,144,288],
 [11,22,44,88,176,352],[13,26,52,104,208],[15,30,60,120,240])


@dataclass(frozen=True)
class NRLDPCCode:
    base_graph: int
    lifting_size: int
    max_iterations: int = 30
    normalization: float = .75

    def __post_init__(self):
        if type(self.base_graph) is not int or self.base_graph not in (1,2):raise ValueError('base_graph must be 1/2')
        if type(self.lifting_size) is not int or not any(self.lifting_size in s for s in LIFTING_SETS):raise ValueError('invalid lifting_size')
        if type(self.max_iterations) is not int or self.max_iterations<1:raise ValueError('positive iterations required')
        if isinstance(self.normalization,bool) or not np.isfinite(self.normalization) or not 0<self.normalization<=1:raise ValueError('normalization must be (0,1]')

    @property
    def n_bits(self):return (22 if self.base_graph==1 else 10)*self.lifting_size

    @property
    def code_length(self):return (66 if self.base_graph==1 else 50)*self.lifting_size

    def check_rows(self):
        table=json.loads(Path(__file__).with_name('_coding_tables.json').read_text())['ldpc'][str(self.base_graph)]
        z=self.lifting_size;iset=next(i for i,s in enumerate(LIFTING_SETS) if z in s)
        rows=[[] for _ in range((46 if self.base_graph==1 else 42)*z)]
        for key,shifts in table.items():
            r,c=map(int,key.split(','));shift=shifts[iset]%z
            for t in range(z):rows[r*z+t].append(c*z+(t+shift)%z)
        return [np.array(r,dtype=int) for r in rows]

    def encode(self,bits):
        v=np.asarray(bits)
        if v.shape!=(self.n_bits,) or v.dtype.kind not in 'iu' or np.any((v < -1)|(v>1)):raise ValueError('integer [K], bits 0/1 or filler -1 required')
        filler=v==-1;v=np.where(filler,0,v).astype(np.int8);pivots={}
        for indices in self.check_rows():
            cols=set(int(i-self.n_bits) for i in indices if i>=self.n_bits)
            rhs=int(np.sum(v[indices[indices<self.n_bits]])%2)
            while cols:
                pivot=min(cols)
                if pivot not in pivots:pivots[pivot]=(cols,rhs);break
                other,value=pivots[pivot];cols=cols^other;rhs^=value
            if not cols and rhs:raise RuntimeError('inconsistent parity equations')
        parity=np.zeros(self.code_length+2*self.lifting_size-self.n_bits,dtype=np.int8)
        if len(pivots)!=len(parity):raise RuntimeError('rank-deficient parity matrix')
        for pivot in sorted(pivots,reverse=True):
            cols,rhs=pivots[pivot];parity[pivot]=rhs ^ (int(np.sum(parity[list(cols-{pivot})]))%2)
        full=np.concatenate([v,parity]);full[:self.n_bits][filler]=-1
        return full[2*self.lifting_size:]

    def decode(self,llr,filler_positions=()):
        values=np.asarray(llr,dtype=float)
        if values.shape!=(self.code_length,) or not np.all(np.isfinite(values)):raise ValueError('finite LLR [N] required')
        filler=np.asarray(tuple(filler_positions),dtype=int)
        if np.any(filler<0) or np.any(filler>=self.n_bits):raise ValueError('invalid filler positions')
        posterior=np.concatenate([np.zeros(2*self.lifting_size),np.clip(values,-1e4,1e4)])
        posterior[filler]=1e6;rows=self.check_rows();messages=[np.zeros(len(r)) for r in rows]
        converged=False
        for iteration in range(1,self.max_iterations+1):
            for j,idx in enumerate(rows):
                q=posterior[idx]-messages[j];sign=np.where(q<0,-1.,1.);a=abs(q)
                smallest=int(np.argmin(a));first=a[smallest];second=np.partition(a,1)[1]
                magnitude=np.full(len(q),first);magnitude[smallest]=second
                messages[j]=self.normalization*np.prod(sign)*sign*magnitude
                posterior[idx]=q+messages[j]
            posterior[filler]=1e6
            hard=(posterior<0).astype(np.int8)
            if all(int(np.sum(hard[r]))%2==0 for r in rows):converged=True;break
        return dict(bits=hard[:self.n_bits],converged=converged,iterations=iteration)
