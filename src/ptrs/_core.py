"""Fixed R15 CP-OFDM PT-RS; excludes transform precoding and hopping."""
import numpy as np
from common.NRCommon import _integer
from common import NRCommon
from common._validation import real_value
from grid import NRGrid

# 38.211 V15.2.0 tables 6.4.1.2.2.1-1 and 7.4.1.2.2-1.
OFFSETS={1:((0,2,6,8),(2,4,8,10),(1,3,7,9),(3,5,9,11)),
         2:((0,1,6,7),(1,6,7,0),(2,3,8,9),(3,8,9,2),(4,5,10,11),(5,10,11,4))}

def validate(obj,kind):
    if not isinstance(obj.resource,kind):
        raise TypeError('resource has wrong direction/type')
    r=obj.resource
    if r.n_layers!=1:
        raise ValueError('first release requires one layer')
    _integer('time_density',obj.time_density,1,4)
    if obj.time_density not in (1,2,4):
        raise ValueError('time_density must be 1/2/4')
    _integer('frequency_density',obj.frequency_density,2,4)
    if obj.frequency_density not in (2,4):
        raise ValueError('frequency_density must be 2/4')
    _integer('re_offset',obj.re_offset,0,3)
    if r.dmrs_ports[0]>=len(OFFSETS[r.dmrs_configuration_type]):
        raise ValueError('associated DMRS port absent from R15 PTRS table')

def symbols(obj):
    r=obj.resource;result=[];ref=0;i=0;previous=-1
    dmrs=set(int(l)-r.start_symbol for l in r.dmrs_symbols)
    while ref+i*obj.time_density<r.n_symbols:
        target=ref+i*obj.time_density
        hit=[l for l in dmrs if max(previous+1,ref)<=l<=target]
        if hit:
            ref=max(hit);i=1;previous=ref
        else:
            result.append(r.start_symbol+target);previous=target;i+=1
    return np.array(result,dtype=int)

def positions(obj):
    r=obj.resource;K=obj.frequency_density;tail=r.n_prbs%K
    rb0=r.rnti%(tail if tail else K)
    offset=OFFSETS[r.dmrs_configuration_type][r.dmrs_ports[0]][obj.re_offset]
    first=12*(r.cell.bwp_start-r.cell.n_start_grid+r.prb)
    return [(0,int(l),first+12*b+offset) for l in symbols(obj)
            for b in range(rb0,r.n_prbs,K)]

def generate(obj):
    r=obj.resource;idx=positions(obj);out=[]
    l=int(r.dmrs_symbols[0]);nid=r.dmrs_scrambling_id
    seed=(2**17*(r.cell.symbols_per_slot*r.cell.n_slot+l+1)*(2*nid+1)+2*nid+r.n_scid)%2**31
    port=r.dmrs_ports[0];group,_,_=r.port_parameters(port)
    for _,_,k in idx:
        absolute=k+12*r.cell.n_start_grid
        local=absolute%12
        if r.dmrs_configuration_type==1:
            m=(absolute-group)//2
        else:
            m=(absolute//6)*2+(local%6-2*group)
        b=NRCommon.gold_sequence(seed,2,offset=2*m).astype(int)
        out.append(((1-2*b[0])+1j*(1-2*b[1]))/np.sqrt(2))
    return np.array(out,dtype=complex)

def mapping(obj,grid,beta):
    r=obj.resource
    if not isinstance(grid,NRGrid) or grid.cell!=r.cell or grid.n_ports!=1:
        raise ValueError('matching single-port NRGrid required')
    return grid.map(obj.indices(),real_value('beta',beta,0)*obj.generate(),owner='PTRS')

def estimate(obj,rx_grid,channel_estimates):
    r=obj.resource;y=np.asarray(rx_grid,dtype=complex);h=np.asarray(channel_estimates,dtype=complex)
    if y.shape!=(r.cell.n_rx_antennas,r.cell.symbols_per_slot,r.cell.n_subcarriers) or not np.all(np.isfinite(y)):
        raise ValueError('finite [Rx,symbol,k] required')
    if h.shape!=(r.cell.n_rx_antennas,) or not np.all(np.isfinite(h)) or not np.any(abs(h)>0):
        raise ValueError('nonzero finite flat [Rx] channel estimates required')
    idx=obj.indices();x=obj.generate();ls=symbols(obj);phase=[]
    for l in ls:
        mask=idx[:,1]==l
        projection=np.sum(h.conj()[:,None]*y[:,idx[mask,1],idx[mask,2]]*x[mask].conj())
        if abs(projection)<1e-20:
            raise ValueError('PT-RS observation has no phase information')
        phase.append(np.angle(projection))
    corrected=y.copy()
    corrected[:,ls,:]*=np.exp(-1j*np.array(phase))[None,:,None]
    return dict(symbols=ls,phase_rad=np.array(phase),corrected_grid=corrected)
