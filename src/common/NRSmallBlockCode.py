"""R15 TS38.212 §5.3.3.3、§5.4.3；仅3..11位UCI，软输入穷举ML译码。"""
import numpy as np
from common.NRCommon import _integer
from common._small_block_tables import SMALL_BLOCK_BASIS


class NRSmallBlockCode:
    @staticmethod
    def encode(bits, output_length):
        values = tuple(bits)
        if not 3 <= len(values) <= 11 or any(isinstance(b,(bool,np.bool_)) or not isinstance(b,(int,np.integer)) or b not in (0,1) for b in values):
            raise ValueError('UCI requires 3..11 integer bits; Polar is not implemented')
        _integer('output_length', output_length, len(values), 8192)
        mother = SMALL_BLOCK_BASIS[:,:len(values)] @ np.array(values,dtype=np.int64)%2
        return mother[np.arange(output_length)%32].astype(np.int8)

    @staticmethod
    def decode(llr, n_bits):
        _integer('n_bits', n_bits, 3, 11)
        values = np.asarray(llr,dtype=float)
        if values.ndim != 1 or not n_bits <= values.size <= 8192 or not np.all(np.isfinite(values)):
            raise ValueError('llr must be finite 1D, n_bits..8192 entries; positive means bit 0')
        # Rate recovery folds repeated observations into 32 mother-code positions.
        recovered = np.bincount(np.arange(values.size)%32,weights=values,minlength=32)
        candidates = ((np.arange(2**n_bits)[:,None] >> np.arange(n_bits)) & 1).astype(np.int8)
        codewords = candidates @ SMALL_BLOCK_BASIS[:,:n_bits].T%2
        scores = (1-2*codewords) @ recovered
        return candidates[int(np.argmax(scores))].tolist()
