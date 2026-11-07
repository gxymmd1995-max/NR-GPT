"""R15 TS38.211 §5.1: Gray-labelled unit-average-energy QPSK/16/64/256QAM.

Reusable numerical helper. Rows use MSB-first bit labels, even bit indices I,
odd indices Q. Returns complex[2^Qm], int8[2^Qm,Qm].
"""
import numpy as np


def constellation(modulation_order):
    if type(modulation_order) is not int or modulation_order not in (2,4,6,8):
        raise ValueError('Qm must be 2,4,6,8')
    qm=modulation_order
    labels=((np.arange(2**qm)[:,None]>>np.arange(qm-1,-1,-1))&1).astype(np.int8)
    axes=[]
    for parity in (0,1):
        bits=labels[:,parity::2];amplitude=1-2*bits[:,-1].astype(int)
        for j in range(bits.shape[1]-2,-1,-1):
            amplitude=(1-2*bits[:,j])*(2**(bits.shape[1]-1-j)-amplitude)
        axes.append(amplitude)
    return (axes[0]+1j*axes[1])/np.sqrt(2/3*(2**qm-1)),labels
