function export_NRPUCCH3_reference
cases={};rng(123);id=0;
for L=4:14
 for mode=0:1
 id=id+1;bands=[1 2 3 6];P=bands(mod(id-1,4)+1);hop=mod(id,3)~=0;extra=mod(id,2)==0;
 modulation='QPSK';if mode,modulation='pi/2-BPSK';end
 carrier=nrCarrierConfig('NCellID',17,'NSizeGrid',24,'SubcarrierSpacing',30,'NSlot',3);
 cfg=nrPUCCH3Config('PRBSet',1:P,'SymbolAllocation',[0 L],'NID',731,'RNTI',4321,...
   'HoppingID',271,'GroupHopping','enable','AdditionalDMRS',extra,'Modulation',modulation);
 if hop,cfg.FrequencyHopping='intraSlot';cfg.SecondHopStartPRB=12;end
 di=nrPUCCHIndices(carrier,cfg);pi=nrPUCCHDMRSIndices(carrier,cfg);
 E=numel(di)*(2-mode);A=min(32,max(7,floor(.3*E)-11));if A<12,A=7;end
 b=randi([0 1],A,1);coded=nrUCIEncode(b,E);
 data=nrPUCCH3(coded,modulation,731,4321,P);pilot=nrPUCCHDMRS(carrier,cfg);
 grid=nrResourceGrid(carrier,1);grid(di)=data;grid(pi)=pilot;
 wave=nrOFDMModulate(carrier,grid,'Nfft',512,'Windowing',0);rx=wave*[.7+.4j -.3+.6j];
 cases{end+1}=struct('L',L,'P',P,'hop',hop,'extra',extra,'modulation',modulation,'A',A,'E',E,...
   'bits',b,'coded',coded,'grid_real',real(grid(:)),'grid_imag',imag(grid(:)),...
   'wave_real',real(rx(:)),'wave_imag',imag(rx(:)));
 end
end
result=struct('matlab_version',version,'toolbox',ver('5g'),'cases',{cases});
fid=fopen(fullfile(fileparts(mfilename('fullpath')),'NRPUCCH3_reference.json'),'w');fwrite(fid,jsonencode(result),'char');fclose(fid);
end
