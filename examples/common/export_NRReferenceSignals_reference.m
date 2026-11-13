function export_NRReferenceSignals_reference
% Actual R2024a 5G Toolbox vectors. Fixed R15 subset only.
carrier=nrCarrierConfig; carrier.NSizeGrid=52; carrier.SubcarrierSpacing=30;
records={};
for row=[1 2]
 for density=[0.5 1 3]
  if (row==1 && density~=3)||(row==2 && density==3), continue; end
  c=nrCSIRSConfig; c.CSIRSType='nzp';c.CSIRSPeriod='on';c.RowNumber=row;
  if density==3,c.Density='three';else,c.Density='one';end;c.SymbolLocations=4;c.SubcarrierLocations=0;
  c.NumRB=24;c.RBOffset=0;c.NID=0;
  if density==0.5,c.Density='dot5even';end
  x=nrCSIRS(carrier,c);idx=nrCSIRSIndices(carrier,c,'IndexStyle','subscript','IndexBase','0based');
  records{end+1}=struct('kind','CSI','row',row,'density',density,'indices',double(idx(:,[3 2 1])), 'real',real(x),'imag',imag(x));
 end
end
for uplink=[false true]
 for td=[1 2 4]
  for fd=[2 4]
   for type=[1 2]
    for offset=0:3
     if uplink,p=nrPUSCHConfig; else,p=nrPDSCHConfig;end
     p.PRBSet=0:3;p.SymbolAllocation=[0 14];p.RNTI=1;p.EnablePTRS=1;
     p.DMRS.DMRSTypeAPosition=2;p.DMRS.DMRSAdditionalPosition=0;
     p.DMRS.DMRSConfigurationType=type;p.DMRS.DMRSLength=1;
     p.PTRS.TimeDensity=td;p.PTRS.FrequencyDensity=fd;p.PTRS.REOffset=dec2bin(offset,2);
     if uplink,x=nrPUSCHPTRS(carrier,p);idx=nrPUSCHPTRSIndices(carrier,p,'IndexStyle','subscript','IndexBase','0based');
     else,x=nrPDSCHPTRS(carrier,p);idx=nrPDSCHPTRSIndices(carrier,p,'IndexStyle','subscript','IndexBase','0based');end
     records{end+1}=struct('kind',string(char('D'+uplink*17)),'uplink',uplink,'td',td,'fd',fd,'dmrs_type',type,'offset',offset,'indices',double(idx(:,[3 2 1])), 'real',real(x),'imag',imag(x));
    end
   end
  end
 end
end
% FR1 100 MHz/30 kHz: nonzero carrier/BWP offsets, slot and scrambling IDs.
carrier=nrCarrierConfig('NSizeGrid',273,'NStartGrid',10,'SubcarrierSpacing',30,'NSlot',7);
% Each column is [row; density; parity].
for params=[1 2 2;3 0.5 0.5;0 0 1]
 row=params(1);density=params(2);parity=params(3);
 c=nrCSIRSConfig('CSIRSType','nzp','CSIRSPeriod','on','RowNumber',row, ...
    'SymbolLocations',9,'SubcarrierLocations',3,'NumRB',272,'RBOffset',0,'NID',511);
 if density==3,c.Density='three';
 elseif parity==0,c.Density='dot5even';
 else,c.Density='dot5odd';end
 x=nrCSIRS(carrier,c);idx=nrCSIRSIndices(carrier,c,'IndexStyle','subscript','IndexBase','0based');
 records{end+1}=struct('kind','CSI','grid_size',273,'grid_start',10,'slot',7, ...
    'row',row,'density',density,'parity',parity,'start_rb',10,'n_rbs',272, ...
    'symbol',9,'subcarrier',3,'nid',511,'indices',double(idx(:,[3 2 1])), ...
    'real',real(x),'imag',imag(x));
end
for uplink=[false true]
 if uplink,p=nrPUSCHConfig;else,p=nrPDSCHConfig;end
 p.NStartBWP=15;p.NSizeBWP=260;p.PRBSet=2:258;p.SymbolAllocation=[1 13];
 p.RNTI=39;p.EnablePTRS=1;
 p.DMRS.DMRSTypeAPosition=3;p.DMRS.DMRSAdditionalPosition=1;
 p.DMRS.DMRSConfigurationType=2;p.DMRS.DMRSLength=1;
 p.DMRS.NIDNSCID=117;p.DMRS.NSCID=1;
 p.PTRS.TimeDensity=2;p.PTRS.FrequencyDensity=4;p.PTRS.REOffset='11';
 if uplink,x=nrPUSCHPTRS(carrier,p);idx=nrPUSCHPTRSIndices(carrier,p,'IndexStyle','subscript','IndexBase','0based');
 else,x=nrPDSCHPTRS(carrier,p);idx=nrPDSCHPTRSIndices(carrier,p,'IndexStyle','subscript','IndexBase','0based');end
 records{end+1}=struct('kind',string(char('D'+uplink*17)), ...
    'grid_size',273,'grid_start',10,'slot',7,'bwp_start',15,'bwp_size',260, ...
    'prb',2,'n_prbs',257,'start_symbol',1,'n_symbols',13,'rnti',39,'dmrs_pos',3, ...
    'dmrs_additional',1,'nid',117,'n_scid',1,'uplink',uplink,'td',2,'fd',4, ...
    'dmrs_type',2,'offset',3,'indices',double(idx(:,[3 2 1])),'real',real(x),'imag',imag(x));
end
% Shared-channel data mapping with PT-RS enabled. Save Toolbox G and full
% data coordinates together with deterministic bits and scrambled QPSK.
carrier=nrCarrierConfig('NSizeGrid',52,'NStartGrid',10,'SubcarrierSpacing',30,'NSlot',3);
for uplink=[false true]
 for typ=[1 2]
  if uplink,p=nrPUSCHConfig;else,p=nrPDSCHConfig;end
  p.NStartBWP=12;p.NSizeBWP=24;p.PRBSet=1:5;p.SymbolAllocation=[0 14];
  p.RNTI=39;p.NID=17;p.EnablePTRS=1;
  p.DMRS.DMRSTypeAPosition=2;p.DMRS.DMRSAdditionalPosition=0;
  p.DMRS.DMRSConfigurationType=typ;p.DMRS.DMRSLength=1;
  p.DMRS.NumCDMGroupsWithoutData=1;
  p.PTRS.TimeDensity=2;p.PTRS.FrequencyDensity=2;p.PTRS.REOffset='01';
  if uplink
   [di,info]=nrPUSCHIndices(carrier,p,'IndexStyle','subscript','IndexBase','0based');
   bits=mod(floor((0:info.G-1)'/3),2);data=nrPUSCH(carrier,p,bits);
   pi=nrPUSCHPTRSIndices(carrier,p,'IndexStyle','subscript','IndexBase','0based');
   pilot=nrPUSCHPTRS(carrier,p);
  else
   [di,info]=nrPDSCHIndices(carrier,p,'IndexStyle','subscript','IndexBase','0based');
   bits=mod(floor((0:info.G-1)'/3),2);data=nrPDSCH(carrier,p,bits);
   pi=nrPDSCHPTRSIndices(carrier,p,'IndexStyle','subscript','IndexBase','0based');
   pilot=nrPDSCHPTRS(carrier,p);
  end
  records{end+1}=struct('kind','shared','uplink',uplink,'grid_size',52,'grid_start',10, ...
     'slot',3,'bwp_start',12,'bwp_size',24,'prb',1,'n_prbs',5,'rnti',39, ...
     'data_nid',17,'dmrs_type',typ,'cdm_groups',1,'td',2,'fd',2,'offset',1,'G',info.G,'bits',bits, ...
     'indices',double(pi(:,[3 2 1])),'real',real(pilot),'imag',imag(pilot), ...
     'data_indices',double(di(:,[3 2 1])),'data_real',real(data),'data_imag',imag(data));
 end
end
v=ver('5g');out=struct('matlab_version',version,'toolbox_version',v.Version,'cases',{records});
root=fileparts(mfilename('fullpath'));f=fopen(fullfile(root,'NRReferenceSignals_reference.json'),'w');fwrite(f,jsonencode(out));fclose(f);
fprintf('Exported %d actual Toolbox cases\n',numel(records));
end
