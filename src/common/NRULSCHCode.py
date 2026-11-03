"""R15 TS38.212 §6.2, §5.4.2: single-code-block UL-SCH CRC/LDPC/rate matching.

Explicit TBS/target rate, one layer, full circular buffer. No multi-block segmentation/HARQ combining.
"""
from dataclasses import dataclass
import numpy as np
from common.NRCommon import _integer
from common._validation import real_value
from common.NRLDPCCode import NRLDPCCode,LIFTING_SETS


@dataclass(frozen=True)
class NRULSCHCode:
    n_bits: int
    target_code_rate: float
    output_length: int
    modulation_order: int = 2
    redundancy_version: int = 0
    max_iterations: int = 30

    def __post_init__(self):
        _integer('n_bits',self.n_bits,16,8424)
        if self.n_bits%8:raise ValueError('transport block must be byte aligned')
        real_value('target_code_rate',self.target_code_rate,.0001,.95)
        _integer('output_length',self.output_length,1,1000000)
        if type(self.modulation_order) is not int or self.modulation_order not in (2,4,6,8):raise ValueError('invalid modulation order')
        if self.output_length%self.modulation_order:raise ValueError('G must be divisible by Qm')
        _integer('redundancy_version',self.redundancy_version,0,3)
        _integer('max_iterations',self.max_iterations,1,1000)
        if self.n_bits+self.crc_length>(8448 if self.base_graph==1 else 3840):
            raise ValueError('multiple LDPC code blocks not implemented; reduce TBS')

    @property
    def crc_length(self):return 16 if self.n_bits<=3824 else 24

    @property
    def base_graph(self):return 2 if self.n_bits<=292 or (self.n_bits<=3824 and self.target_code_rate<=.67) or self.target_code_rate<=.25 else 1

    @property
    def lifting_size(self):
        B=self.n_bits+self.crc_length
        kb=22 if self.base_graph==1 else 10 if B>640 else 9 if B>560 else 8 if B>192 else 6
        return min(z for group in LIFTING_SETS for z in group if kb*z>=B)

    def ldpc(self):return NRLDPCCode(self.base_graph,self.lifting_size,self.max_iterations)

    @staticmethod
    def crc(bits,length):
        if length not in (16,24):raise ValueError('CRC length must be 16 or 24A')
        polynomial=0x11021 if length==16 else 0x1864cfb
        values=np.concatenate([np.array(bits,dtype=np.int8),np.zeros(length,dtype=np.int8)])
        p=np.array([(polynomial>>i)&1 for i in range(length,-1,-1)],dtype=np.int8)
        for i in range(len(bits)):
            if values[i]:values[i:i+length+1]^=p
        return values[-length:]

    def rate_indices(self):
        code=self.ldpc();z=self.lifting_size
        factors=(0,17,33,56) if self.base_graph==1 else (0,13,25,43)
        start=factors[self.redundancy_version]*z
        cycle=(np.arange(code.code_length)+start)%code.code_length
        # Filler positions in the complete K domain, shifted by the initial 2Z puncturing.
        original=cycle+2*z
        valid=cycle[(original<self.n_bits+self.crc_length)|(original>=code.n_bits)]
        return np.resize(valid,self.output_length)

    def encode(self,bits):
        v=np.asarray(bits)
        if v.shape!=(self.n_bits,) or v.dtype.kind not in 'iu' or np.any((v!=0)&(v!=1)):raise ValueError('binary integer transport block [A] required')
        code=self.ldpc();block=np.full(code.n_bits,-1,dtype=np.int8)
        block[:self.n_bits+self.crc_length]=np.concatenate([v,self.crc(v,self.crc_length)])
        mother=code.encode(block);selected=mother[self.rate_indices()]
        return selected.reshape(self.modulation_order,-1).T.ravel()

    def decode(self,llr):
        v=np.asarray(llr,dtype=float)
        if v.shape!=(self.output_length,) or not np.all(np.isfinite(v)):raise ValueError('finite soft input [G] required')
        code=self.ldpc();selected=v.reshape(-1,self.modulation_order).T.ravel()
        recovered=np.zeros(code.code_length);np.add.at(recovered,self.rate_indices(),selected)
        result=code.decode(recovered,range(self.n_bits+self.crc_length,code.n_bits))
        b=result['bits'];payload=b[:self.n_bits]
        return dict(bits=payload.tolist(),crc_ok=bool(result['converged'] and np.array_equal(self.crc(payload,self.crc_length),b[self.n_bits:self.n_bits+self.crc_length])),
                    converged=result['converged'],iterations=result['iterations'])
