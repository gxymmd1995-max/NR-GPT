function export_NRPUCCH4_reference
% Actual Toolbox F4 all OCCs, lengths and both modulation schemes.
cases={};rng(123);id=0;
for L=4:14
 for sf=[2 4]
  for occ=0:sf-1
   for mode=0:1
    id=id+1;hop=mod(id,3)~=0;extra=mod(id,2)==0;
    modulation='QPSK';if mode,modulation='pi/2-BPSK';end
    carrier=nrCarrierConfig('NCellID',17,'NSizeGrid',6,'NStartGrid',10,'SubcarrierSpacing',30,'NSlot',3);
    cfg=nrPUCCH4Config('NStartBWP',11,'NSizeBWP',4,'PRBSet',1,'SymbolAllocation',[0 L],...
      'NID',731,'RNTI',4321,'HoppingID',271,'GroupHopping','enable',...
      'AdditionalDMRS',extra,'Modulation',modulation,'SpreadingFactor',sf,'OCCI',occ);
    if hop,cfg.FrequencyHopping='intraSlot';cfg.SecondHopStartPRB=3;end
    di=nrPUCCHIndices(carrier,cfg);pi=nrPUCCHDMRSIndices(carrier,cfg);
    E=numel(di)*(2-mode)/sf;A=min(32,max(3,floor(.3*E)-11));
    if A<12,A=min(7,max(3,floor(.5*E)));end
    if E>=36 && A<12,A=12;end
    b=randi([0 1],A,1);coded=nrUCIEncode(b,E);
    grid=nrResourceGrid(carrier,1);
    grid(di)=nrPUCCH4(coded,modulation,731,4321,sf,occ);
    grid(pi)=nrPUCCHDMRS(carrier,cfg);
    wave=nrOFDMModulate(carrier,grid,'Nfft',128,'Windowing',0);rx=wave*[.7+.4j -.3+.6j];
    cases{end+1}=struct('L',L,'sf',sf,'occ',occ,'hop',hop,'extra',extra,'modulation',modulation,...
      'A',A,'E',E,'bits',b,'coded',coded,'grid_real',real(grid(:)),'grid_imag',imag(grid(:)),...
      'wave_real',real(rx(:)),'wave_imag',imag(rx(:)));
   end
  end
 end
end
result=struct('matlab_version',version,'toolbox',ver('5g'),'cases',{cases});
fid=fopen(fullfile(fileparts(mfilename('fullpath')),'NRPUCCH4_reference.json'),'w');fwrite(fid,jsonencode(result),'char');fclose(fid);
fprintf('Exported %d actual F4 cases\n',numel(cases));
end
