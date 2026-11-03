"""Binary Reed–Muller RM(r,m), polynomial evaluation encoding and majority decoding.

This is classical RM, distinct from the R15 (32,K) small-block basis.
"""
from dataclasses import dataclass
from itertools import combinations
import numpy as np


@dataclass(frozen=True)
class NRRMCode:
    order: int = 1
    n_variables: int = 5

    def __post_init__(self):
        if type(self.n_variables) is not int or not 1<=self.n_variables<=10:raise ValueError('n_variables must be 1..10')
        if type(self.order) is not int or not 0<=self.order<=self.n_variables:raise ValueError('order must be 0..m')

    def monomials(self):return [tuple(c) for degree in range(self.order+1) for c in combinations(range(self.n_variables),degree)]

    @property
    def n_bits(self):return len(self.monomials())

    @property
    def code_length(self):return 2**self.n_variables

    def generator(self):
        points=(np.arange(self.code_length)[:,None]>>np.arange(self.n_variables))&1
        return np.array([np.prod(points[:,list(term)],axis=1) for term in self.monomials()],dtype=np.int8)

    def encode(self,bits):
        v=np.asarray(bits)
        if v.shape!=(self.n_bits,) or v.dtype.kind not in 'iu' or np.any((v!=0)&(v!=1)):raise ValueError('binary integer [K] required')
        return (v.astype(np.int64)@self.generator()%2).astype(np.int8)

    def decode(self,llr):
        v=np.asarray(llr,dtype=float)
        if v.shape!=(self.code_length,) or not np.all(np.isfinite(v)):raise ValueError('finite LLR [N] required')
        residual=(v<0).astype(np.int8);terms=self.monomials();g=self.generator();bits=np.zeros(self.n_bits,dtype=np.int8)
        for degree in range(self.order,-1,-1):
            remove=np.zeros_like(residual)
            for j,term in enumerate(terms):
                if len(term)!=degree:continue
                mask=sum(1<<i for i in term);votes=[]
                inside=[n for n in range(self.code_length) if n&~mask==0]
                for base in range(self.code_length):
                    if base&mask==0:votes.append(int(np.sum(residual[np.array(inside)|base]))%2)
                bits[j]=int(sum(votes)>len(votes)/2);remove^=bits[j]*g[j]
            residual^=remove
        return bits
