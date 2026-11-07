"""TS38.212 V15.2.0 §5.3.1 mother-code kernel, SC decoder; no CRC/rate matching/PC bits."""
from dataclasses import dataclass
import json
from pathlib import Path
import numpy as np


@dataclass(frozen=True)
class NRPolarCode:
    n_bits: int
    code_length: int
    input_interleaving: bool = False

    def __post_init__(self):
        if type(self.code_length) is not int or self.code_length not in (32,64,128,256,512,1024):
            raise ValueError('code_length must be 2^n, n=5..10')
        if type(self.n_bits) is not int or not 1<=self.n_bits<=self.code_length:
            raise ValueError('invalid n_bits')
        if type(self.input_interleaving) is not bool:
            raise TypeError('input_interleaving must be bool')
        if self.input_interleaving and self.n_bits>164:
            raise ValueError('interleaver supports K<=164')

    def information_indices(self):
        table=json.loads(Path(__file__).with_name('_coding_tables.json').read_text())['reliability']
        return np.sort([i for i in table if i<self.code_length][-self.n_bits:])

    def permutation(self):
        if not self.input_interleaving:
            return np.arange(self.n_bits)
        table=json.loads(Path(__file__).with_name('_coding_tables.json').read_text())['interleaver']
        return np.array([i-(164-self.n_bits) for i in table if i>=164-self.n_bits])

    def encode(self,bits):
        v=np.asarray(bits)
        if v.shape!=(self.n_bits,) or v.dtype.kind not in 'iu' or np.any((v!=0)&(v!=1)):
            raise ValueError('bits must be binary integer [K]')
        x=np.zeros(self.code_length,dtype=np.int8);x[self.information_indices()]=v[self.permutation()]
        return self.transform(x)

    @staticmethod
    def transform(bits):
        """GF(2) mother-code butterfly; input binary vector of power-of-two length."""
        x=np.array(bits,dtype=np.int8,copy=True)
        if x.ndim!=1 or x.size<1 or x.size&(x.size-1) or np.any((x!=0)&(x!=1)):
            raise ValueError('binary power-of-two vector required')
        step=1
        while step<len(x):
            for start in range(0,len(x),2*step):
                x[start:start+step]^=x[start+step:start+2*step]
            step*=2
        return x

    def decode(self,llr):
        values=np.asarray(llr,dtype=float)
        if values.shape!=(self.code_length,) or not np.all(np.isfinite(values)):
            raise ValueError('finite LLR [N] required, positive supports zero')
        info=set(self.information_indices());decisions=np.zeros(self.code_length,dtype=np.int8)
        def visit(a,offset):
            if len(a)==1:
                bit=int(a[0]<0) if offset in info else 0
                decisions[offset]=bit
                return np.array([bit],dtype=np.int8)
            half=len(a)//2;l=a[:half];r=a[half:]
            left=visit(np.sign(l)*np.sign(r)*np.minimum(abs(l),abs(r)),offset)
            right=visit(r+(1-2*left)*l,offset+half)
            return np.concatenate([left^right,right])
        visit(values,0)
        out=np.empty(self.n_bits,dtype=np.int8);out[self.permutation()]=decisions[self.information_indices()]
        return out
