function export_NRPUCCH1_reference
% Actual R2024a Toolbox vectors; R15 14*slot sequence addressing adapter.
cases={}; id=0;
for L=4:14
 for hopping=0:1
  count=floor(L/2);if hopping,count=floor(L/4);end
  for occ=0:count-1
   id=id+1; bits=mod([id id+1],2).';
   carrier=nrCarrierConfig('NSizeGrid',6,'NCellID',17,'NSlot',3,'SubcarrierSpacing',30);
   cfg=nrPUCCH1Config('PRBSet',1,'SymbolAllocation',[0 L],...
       'InitialCyclicShift',mod(id,12),'HoppingID',731,'GroupHopping','enable','OCCI',occ);
   if hopping,cfg.FrequencyHopping='intraSlot';cfg.SecondHopStartPRB=4;end
   g=nrResourceGrid(carrier,1);
   hoppingName='disabled';if hopping,hoppingName='enabled';end
   g(nrPUCCHIndices(carrier,cfg))=nrPUCCH1(bits,[],[0 L],'normal',3,731,'enable',mod(id,12),hoppingName,occ);
   g(nrPUCCHDMRSIndices(carrier,cfg))=nrPUCCHDMRS(carrier,cfg);
   wave=nrOFDMModulate(carrier,g,'Nfft',128,'Windowing',0);
   h=[.7+.4j -.3+.6j]; received=wave*h;
   c=struct('length',L,'hopping',hopping,'occ',occ,'shift',mod(id,12),'bits',bits,...
       'grid_real',real(g(:)),'grid_imag',imag(g(:)),...
       'wave_real',real(received(:)),'wave_imag',imag(received(:)));
   cases{end+1}=c;
  end
 end
end
result=struct('matlab_version',version,'toolbox',ver('5g'),'cases',{cases});
out=fullfile(fileparts(mfilename('fullpath')),'NRPUCCH1_reference.json');
fid=fopen(out,'w');fwrite(fid,jsonencode(result),'char');fclose(fid);
fprintf('Exported %d actual F1 cases\n',numel(cases));
end
