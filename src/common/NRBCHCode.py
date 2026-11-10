"""TS38.212 V15.2.0 §7.1: 24-bit BCH/MIB plus timing, payload scrambling, CRC24C and Polar."""
from dataclasses import dataclass
import numpy as np
from common.NRCommon import NRCommon,_integer
from common.NRPolarCode import NRPolarCode
from common.NRUCICode import SUBBLOCK

G=np.array([16,23,18,17,8,30,10,6,24,7,0,5,3,2,1,4,9,11,12,13,14,15,19,20,21,22,25,26,27,28,29,31])

@dataclass(frozen=True)
class NRBCHCode:
    cell_id: int
    l_max: int = 8
    ssb_index: int = 0
    half_frame: int = 0
    k_ssb: int = 0

    def __post_init__(self):
        _integer('cell_id',self.cell_id,0,1007)
        if type(self.l_max) is not int or self.l_max not in (4,8,64):
            raise ValueError('l_max must be 4/8/64')
        _integer('ssb_index',self.ssb_index,0,self.l_max-1)
        _integer('half_frame',self.half_frame,0,1)
        _integer('k_ssb',self.k_ssb,0,23)

    def payload_permutation(self):
        sfn=iter(G[:10]);other=iter(G[14:]);result=[]
        for i in range(32):
            if i in (*range(1,7),*range(24,28)):
                result.append(next(sfn))
            elif i==28:
                result.append(G[10])
            elif i>=29:
                result.append(G[11+i-29])
            else:
                result.append(next(other))
        return np.array(result)

    def payload_scrambling(self,payload):
        mask=np.ones(32,bool);mask[G[[7,8,10]]]=False
        if self.l_max==64:
            mask[G[11:14]]=False
        v=2*int(payload[G[7]])+int(payload[G[8]])
        out=np.array(payload,copy=True);M=int(mask.sum())
        out[mask]^=NRCommon.gold_sequence(self.cell_id,M,offset=v*M)
        return out

    @staticmethod
    def crc(bits):
        work=np.concatenate([bits,np.zeros(24,dtype=np.int8)])
        poly=np.array([(0x1b2b117>>i)&1 for i in range(24,-1,-1)],dtype=np.int8)
        for i in range(len(bits)):
            if work[i]:
                work[i:i+25]^=poly
        return work[-24:]

    def encode(self,mib,sfn_lsb=0):
        mib=np.asarray(mib)
        if mib.shape!=(24,) or mib.dtype.kind not in 'iu' or np.any((mib!=0)&(mib!=1)):
            raise ValueError('binary integer MIB transport block [24] required')
        _integer('sfn_lsb',sfn_lsb,0,15)
        tail=[(sfn_lsb>>i)&1 for i in (3,2,1,0)]+[self.half_frame]
        tail += [(self.ssb_index>>i)&1 for i in (5,4,3)] if self.l_max==64 else [self.k_ssb//16,0,0]
        raw=np.concatenate([mib,tail]).astype(np.int8);a=np.empty(32,dtype=np.int8);a[self.payload_permutation()]=raw
        scrambled=self.payload_scrambling(a);message=np.concatenate([scrambled,self.crc(scrambled)])
        encoded=NRPolarCode(56,512,True).encode(message)
        j=SUBBLOCK[np.arange(512)//16]*16+np.arange(512)%16
        return encoded[j][np.arange(864)%512]

    def decode(self,llr):
        v=np.asarray(llr,dtype=float)
        if v.shape!=(864,) or not np.all(np.isfinite(v)):
            raise ValueError('finite BCH soft input [864] required')
        y=np.zeros(512);np.add.at(y,np.arange(864)%512,v)
        j=SUBBLOCK[np.arange(512)//16]*16+np.arange(512)%16
        mother=np.empty(512);mother[j]=y
        message=NRPolarCode(56,512,True).decode(mother)
        crc_ok=bool(np.array_equal(self.crc(message[:32]),message[32:]))
        raw=self.payload_scrambling(message[:32])[self.payload_permutation()]
        return dict(mib=raw[:24].tolist(),sfn_lsb=int(raw[24:28]@np.array([8,4,2,1])),
            system_frame_number=int(raw[1:7]@np.array([32,16,8,4,2,1]))*16+int(raw[24:28]@np.array([8,4,2,1])),half_frame=int(raw[28]),
            extra_bits=raw[29:32].tolist(),crc_ok=crc_ok)
