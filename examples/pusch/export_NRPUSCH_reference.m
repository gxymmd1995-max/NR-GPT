function export_NRPUSCH_reference
% Fixed R15 subset: one layer, CP-OFDM, type-A/type1/length1 DMRS, no PTRS/UCI.
cases={};rng(123);id=0;
for rate=[.5 .8]
 for modulation={'QPSK','16QAM','64QAM','256QAM'}
  for rv=0:3
   id=id+1;modname=modulation{1};groups=1+mod(id,2);scid=mod(id,2);pos=2+mod(id,2);
   carrier=nrCarrierConfig('NCellID',17,'NSizeGrid',12,'NStartGrid',10,'SubcarrierSpacing',30,'NSlot',3);
   cfg=nrPUSCHConfig('NStartBWP',11,'NSizeBWP',10,'PRBSet',1:8,'SymbolAllocation',[0 12],...
      'MappingType','A','NumLayers',1,'Modulation',modname,'NID',731,'RNTI',4321,'TransformPrecoding',false);
   cfg.EnablePTRS=false;cfg.DMRS.DMRSConfigurationType=1;cfg.DMRS.DMRSTypeAPosition=pos;
   cfg.DMRS.DMRSAdditionalPosition=0;cfg.DMRS.DMRSLength=1;cfg.DMRS.DMRSPortSet=0;
   cfg.DMRS.NumCDMGroupsWithoutData=groups;cfg.DMRS.NIDNSCID=271;cfg.DMRS.NSCID=scid;
   [di,info]=nrPUSCHIndices(carrier,cfg);pi=nrPUSCHDMRSIndices(carrier,cfg);G=info.G;
   A=512;if rate==.5,A=256;end
   b=randi([0 1],A,1);coding=nrDLSCHInfo(A,rate);
   tb=nrCRCEncode(b,coding.CRC);blocks=nrCodeBlockSegmentLDPC(tb,coding.BGN);
   encoded=nrLDPCEncode(blocks,coding.BGN);coded=nrRateMatchLDPC(encoded,G,rv,modname,1);
   grid=nrResourceGrid(carrier,1);grid(di)=nrPUSCH(carrier,cfg,coded);grid(pi)=nrPUSCHDMRS(carrier,cfg);
   wave=nrOFDMModulate(carrier,grid,'Nfft',256,'Windowing',0);rx=wave*[.7+.4j -.3+.6j];
   cases{end+1}=struct('rate',rate,'modulation',modname,'rv',rv,'groups',groups,'scid',scid,'position',pos,...
      'A',A,'G',G,'bg',coding.BGN,'Z',coding.Zc,'bits',b,'coded',coded,...
      'grid_real',real(grid(:)),'grid_imag',imag(grid(:)),'wave_real',real(rx(:)),'wave_imag',imag(rx(:)));
  end
 end
end
result=struct('matlab_version',version,'toolbox',ver('5g'),'cases',{cases});
fid=fopen(fullfile(fileparts(mfilename('fullpath')),'NRPUSCH_reference.json'),'w');fwrite(fid,jsonencode(result),'char');fclose(fid);
fprintf('Exported %d actual PUSCH cases\n',numel(cases));
end
