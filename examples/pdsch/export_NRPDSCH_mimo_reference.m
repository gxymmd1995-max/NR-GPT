function export_NRPDSCH_mimo_reference
% Actual R15 one-codeword layer mapping/DMRS ports/time-frequency OCC/MIMO waveform.
cases={};rng(123);id=0;
for layers=1:4
 for type=1:2
  for len=1:2
   for variant=0:3
    id=id+1;durations=[8 10 12 14];L=durations(mod(id-1,4)+1);
    additional=mod(id,4);if len==2,additional=mod(variant,2);end
    pos=2+mod(id,2);if additional==3,pos=2;end
    if len==1
     ports=[3 1 2 0];if type==2,ports=[5 0 4 1];end
    else
     ports=[0 4 3 7];if type==2,ports=[1 7 4 10];end
    end
    ports=ports(1:layers);single=4;if type==2,single=6;end
    groups=max(floor(mod(ports,single)/2))+1;
    mods={'QPSK','16QAM','64QAM','256QAM'};modname=mods{mod(id-1,4)+1};
    carrier=nrCarrierConfig('NCellID',17,'NSizeGrid',6,'NStartGrid',10,'SubcarrierSpacing',30,'NSlot',3);
    cfg=nrPDSCHConfig('NStartBWP',11,'NSizeBWP',4,'PRBSet',1:2,'SymbolAllocation',[0 L],...
      'MappingType','A','NumLayers',layers,'Modulation',modname,'NID',731,'RNTI',4321,'VRBToPRBInterleaving',false);
    cfg.EnablePTRS=false;cfg.DMRS.DMRSConfigurationType=type;cfg.DMRS.DMRSTypeAPosition=pos;
    cfg.DMRS.DMRSAdditionalPosition=additional;cfg.DMRS.DMRSLength=len;cfg.DMRS.DMRSPortSet=ports;
    cfg.DMRS.NumCDMGroupsWithoutData=groups;cfg.DMRS.NIDNSCID=271;cfg.DMRS.NSCID=mod(id,2);
    [di,info]=nrPDSCHIndices(carrier,cfg);pi=nrPDSCHDMRSIndices(carrier,cfg);G=info.G;
    A=64;b=randi([0 1],A,1);coding=nrDLSCHInfo(A,.5);
    blocks=nrCodeBlockSegmentLDPC(nrCRCEncode(b,coding.CRC),coding.BGN);
    encoded=nrLDPCEncode(blocks,coding.BGN);nref=size(encoded,1);
    coded=nrRateMatchLDPC(encoded,G,0,modname,layers,nref);
    grid=nrResourceGrid(carrier,layers);grid(di)=nrPDSCH(carrier,cfg,coded);grid(pi)=nrPDSCHDMRS(carrier,cfg);
    tx=nrOFDMModulate(carrier,grid,'Nfft',128,'Windowing',0);
    H=zeros(4,layers);
    for r=1:4,for t=1:layers,H(r,t)=(.1+.03*r)*exp(1j*.17*r*t)+(r==t)*(1+.1j*t);end,end
    rx=tx*H.';
    cases{end+1}=struct('layers',layers,'type',type,'length',len,'additional',additional,'ports',ports,...
      'groups',groups,'L',L,'position',pos,'scid',mod(id,2),'modulation',modname,'A',A,'G',G,'nref',nref,...
      'bits',b,'coded',coded,'H_real',real(H(:)),'H_imag',imag(H(:)),...
      'grid_real',real(grid(:)),'grid_imag',imag(grid(:)),'wave_real',real(rx(:)),'wave_imag',imag(rx(:)));
   end
  end
 end
end
result=struct('matlab_version',version,'toolbox',ver('5g'),'cases',{cases});
fid=fopen(fullfile(fileparts(mfilename('fullpath')),'NRPDSCH_mimo_reference.json'),'w');fwrite(fid,jsonencode(result),'char');fclose(fid);
fprintf('Exported %d actual PDSCH MIMO cases\n',numel(cases));
end
