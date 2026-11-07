"""R15 TS38.212 §7.2 single-code-block DL-SCH, limited-buffer rate matching.

CRC, BG/Z selection and LDPC are shared with the UL-SCH implementation; DL buffer
selection follows §7.2.5 / §5.4.2.1. Higher-layer Nref/TBS_LBRM selection is external.
"""
from dataclasses import dataclass
import numpy as np
from common.NRCommon import _integer
from common.NRULSCHCode import NRULSCHCode


@dataclass(frozen=True)
class NRDLSCHCode(NRULSCHCode):
    n_ref: int | None = None

    def __post_init__(self):
        super().__post_init__()
        if self.n_ref is not None:
            _integer('n_ref',self.n_ref,1,10000000)

    @property
    def buffer_length(self):
        N=self.ldpc().code_length
        return N if self.n_ref is None else min(N,self.n_ref)

    def rate_indices(self):
        code=self.ldpc();z=self.lifting_size;N=code.code_length;Ncb=self.buffer_length
        coefficients=(0,17,33,56) if self.base_graph==1 else (0,13,25,43)
        start=(coefficients[self.redundancy_version]*Ncb//N)*z
        cycle=(np.arange(Ncb)+start)%Ncb;original=cycle+2*z
        valid=cycle[(original<self.n_bits+self.crc_length)|(original>=code.n_bits)]
        # Ncb>=1 includes index 0; with the supported single-block BG/Z selection,
        # original index 2Z is before the filler region (2Z < B). Thus at least one
        # selectable bit exists even for the smallest valid limited buffer.
        return np.resize(valid,self.output_length)
