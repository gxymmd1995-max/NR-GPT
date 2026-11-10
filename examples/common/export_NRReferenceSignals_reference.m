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
v=ver('5g');out=struct('matlab_version',version,'toolbox_version',v.Version,'cases',{records});
root=fileparts(mfilename('fullpath'));f=fopen(fullfile(root,'NRReferenceSignals_reference.json'),'w');fwrite(f,jsonencode(out));fclose(f);
fprintf('Exported %d actual Toolbox cases\n',numel(records));
end
