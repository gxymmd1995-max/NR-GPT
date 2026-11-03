function export_NRPUCCH2_reference
% Actual toolbox coding, QPSK, DMRS, grid and OFDM; fixed R15 baseline cases.
cases={};id=0;
for A=[3:11 12 19 20 32 48]
 for L=1:2
  crc=0;if A>=12,crc=6;end;if A>=20,crc=11;end
  minP=ceil((A+crc)/(.6*16*L));sizes=[minP max(3,minP)];
  for P=sizes
   id=id+1;hop=mod(id,2)==0 && L==2;
   carrier=nrCarrierConfig('NCellID',17,'NSizeGrid',12,'NStartGrid',10,'NSlot',3,'SubcarrierSpacing',30);
   cfg=nrPUCCH2Config('NStartBWP',11,'NSizeBWP',10,'PRBSet',1:(P),...
       'SymbolAllocation',[8 L],'NID',731,'RNTI',4321,'NID0',271);
   if hop,cfg.FrequencyHopping='intraSlot';cfg.SecondHopStartPRB=6;end
   bits=mod((0:A-1).'+id,2); E=16*P*L;
   coded=nrUCIEncode(bits,E);
   data=nrPUCCH2(coded,731,4321);
   pilot=nrPUCCHDMRS(carrier,cfg);
   grid=nrResourceGrid(carrier,1);
   grid(nrPUCCHIndices(carrier,cfg))=data;
   grid(nrPUCCHDMRSIndices(carrier,cfg))=pilot;
   wave=nrOFDMModulate(carrier,grid,'Nfft',256,'Windowing',0);
   received=wave*[.7+.4j -.3+.6j];
   cases{end+1}=struct('A',A,'L',L,'P',P,'hop',hop,'bits',bits,'coded',coded,...
       'grid_real',real(grid(:)),'grid_imag',imag(grid(:)),...
       'wave_real',real(received(:)),'wave_imag',imag(received(:)));
  end
 end
end
result=struct('matlab_version',version,'toolbox',ver('5g'),'cases',{cases});
fid=fopen(fullfile(fileparts(mfilename('fullpath')),'NRPUCCH2_reference.json'),'w');
fwrite(fid,jsonencode(result),'char');fclose(fid);
fprintf('Exported %d actual F2 cases\n',numel(cases));
end
