"""R15 TS38.212 §6.3.1: small block/Polar, CRC, segmentation and rate matching.

Polar decoding uses PC-constrained min-sum SC, not SCL. LDPC is not a PUCCH code.
"""
from dataclasses import dataclass
import json, math
from pathlib import Path
import numpy as np
from common.NRSmallBlockCode import NRSmallBlockCode
from common.NRPolarCode import NRPolarCode
from common.NRCommon import _integer

SUBBLOCK=np.array([0,1,2,4,3,5,6,7,8,16,9,17,10,18,11,19,12,20,13,21,14,22,15,23,24,25,26,28,27,29,30,31])


@dataclass(frozen=True)
class NRUCICode:
    n_bits: int
    output_length: int

    def __post_init__(self):
        _integer('n_bits',self.n_bits,3,1706)
        _integer('output_length',self.output_length,self.n_bits,32768)
        # F4 pi/2-BPSK with SF=4 can have odd E (3 bits per data symbol).
        if self.n_blocks==2 and self.output_length%2:raise ValueError('two-block UCI requires even E')
        if self.n_bits>=12:
            k=math.ceil(self.n_bits/self.n_blocks)+self.crc_length
            if k+(3 if 18<=k<=25 else 0)>self.output_length//self.n_blocks:
                raise ValueError('insufficient UCI resources including CRC and PC bits')

    @property
    def crc_length(self):return 0 if self.n_bits<12 else 6 if self.n_bits<20 else 11

    @property
    def n_blocks(self):return 2 if (self.n_bits>=360 and self.output_length>=1088) or self.n_bits>=1013 else 1

    @staticmethod
    def crc(bits,length):
        """Returns polynomial remainder; CRC6/CRC11, initial state 0, no mask."""
        if length not in (6,11):raise ValueError('CRC length must be 6 or 11')
        polynomial=0x61 if length==6 else 0xe21
        work=np.concatenate([np.array(bits,dtype=np.int8),np.zeros(length,dtype=np.int8)])
        poly=np.array([(polynomial>>i)&1 for i in range(length,-1,-1)],dtype=np.int8)
        for i in range(len(bits)):
            if work[i]:work[i:i+length+1]^=poly
        return work[-length:]

    def polar_configuration(self):
        k=math.ceil(self.n_bits/self.n_blocks)+self.crc_length;e=self.output_length//self.n_blocks
        n1=math.ceil(math.log2(e))
        if e<=9/8*2**(n1-1) and k/e<9/16:n1-=1
        n=max(5,min(n1,math.ceil(math.log2(8*k)),10));N=2**n
        pc=3 if 18<=k<=25 else 0;wm=int(pc>0 and e-k+3>192)
        j=(SUBBLOCK[np.arange(N)//(N//32)]*(N//32)+np.arange(N)%(N//32)).astype(int)
        forbidden=set()
        if e<N:
            if k/e<=7/16:
                forbidden.update(j[:N-e]);limit=math.ceil(3*N/4-e/2) if e>=3*N/4 else math.ceil(9*N/16-e/4)
                forbidden.update(range(limit))
            else:forbidden.update(j[e:])
        reliability=json.loads(Path(__file__).with_name('_coding_tables.json').read_text())['reliability']
        available=[v for v in reliability if v<N and v not in forbidden]
        if len(available)<k+pc or k+pc>e:raise ValueError('insufficient Polar resources')
        selected=available[-(k+pc):];parity=selected[:pc-wm]
        if wm:
            candidates=selected[pc:];weight=min(int(i).bit_count() for i in candidates)
            parity.append([i for i in candidates if int(i).bit_count()==weight][-1])
        return k,e,N,j,np.sort(selected),set(parity)

    @staticmethod
    def bit_interleaver(e):
        t=math.ceil((math.sqrt(8*e+1)-1)/2);rows=[];counter=0
        for i in range(t):
            rows.append(list(range(counter,counter+t-i)));counter+=t-i
        return np.array([rows[i][j] for j in range(t) for i in range(t-j) if rows[i][j]<e],dtype=int)

    def encode(self,bits):
        v=np.asarray(bits)
        if v.shape!=(self.n_bits,) or v.dtype.kind not in 'iu' or np.any((v!=0)&(v!=1)):raise ValueError('binary integer UCI [A] required')
        if self.n_bits<=11:return NRSmallBlockCode.encode(v,self.output_length)
        k,e,N,j,information,pc=self.polar_configuration();info=set(information)
        padded=np.concatenate([np.zeros((-self.n_bits)%self.n_blocks,dtype=np.int8),v])
        result=[]
        for block in np.split(padded,self.n_blocks):
            message=np.concatenate([block,self.crc(block,self.crc_length)])
            u=np.zeros(N,dtype=np.int8);state=[0]*5;cursor=0
            for n in range(N):
                state=state[1:]+state[:1]
                if n in info:
                    if n in pc:u[n]=state[0]
                    else:u[n]=message[cursor];cursor+=1;state[0]^=int(u[n])
            y=NRPolarCode.transform(u)[j]
            selected=y[np.arange(e)%N] if e>=N else y[N-e:] if k/e<=7/16 else y[:e]
            result.extend(selected[self.bit_interleaver(e)])
        return np.array(result,dtype=np.int8)

    def decode(self,llr):
        values=np.asarray(llr,dtype=float)
        if values.shape!=(self.output_length,) or not np.all(np.isfinite(values)):raise ValueError('finite soft input [E] required')
        if self.n_bits<=11:return dict(bits=NRSmallBlockCode.decode(values,self.n_bits),crc_ok=None)
        k,e,N,j,information,pc=self.polar_configuration();info=set(information);decoded=[];valid=True
        # E is even and split evenly for PUCCH; each block uses floor(E/C).
        for segment in (values[i*e:(i+1)*e] for i in range(self.n_blocks)):
            selected=np.zeros(e);selected[self.bit_interleaver(e)]=segment
            y=np.zeros(N)
            if e>=N:np.add.at(y,np.arange(e)%N,selected)
            elif k/e<=7/16:y[N-e:]=selected
            else:y[:e]=selected;y[e:]=1e6
            a=np.empty(N);a[j]=y;decisions=np.zeros(N,dtype=np.int8);state=[0]*5
            def visit(llrs,offset):
                nonlocal state
                if len(llrs)==1:
                    state=state[1:]+state[:1]
                    bit=state[0] if offset in pc else int(llrs[0]<0) if offset in info else 0
                    decisions[offset]=bit
                    if offset in info and offset not in pc:state[0]^=bit
                    return np.array([bit],dtype=np.int8)
                half=len(llrs)//2;l=llrs[:half];r=llrs[half:]
                left=visit(np.sign(l)*np.sign(r)*np.minimum(abs(l),abs(r)),offset)
                right=visit(r+(1-2*left)*l,offset+half)
                return np.concatenate([left^right,right])
            visit(a,0)
            message=decisions[[i for i in information if i not in pc]]
            payload=message[:-self.crc_length]
            valid &= np.array_equal(self.crc(payload,self.crc_length),message[-self.crc_length:])
            decoded.extend(payload)
        return dict(bits=list(map(int,decoded[-self.n_bits:])),crc_ok=bool(valid))
