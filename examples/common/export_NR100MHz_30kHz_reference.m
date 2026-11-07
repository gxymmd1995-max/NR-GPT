function export_NR100MHz_30kHz_reference
% Fixed R15 38.104 V15.2.0 table5.3.2-1: FR1 100MHz /30kHz ->273RB.
base=fileparts(fileparts(mfilename('fullpath')));
names={'NRPUCCH0','NRPUCCH1','NRPUCCH2','NRPUCCH3','NRPUCCH4','NRPUSCH','NRPDSCH','NRPDCCH','NRPRACH','NRSRS'};
for idx=1:numel(names)
 name=names{idx};carrier=nrCarrierConfig('NCellID',17,'NSizeGrid',273,'SubcarrierSpacing',30);
 g=nrResourceGrid(carrier);b=repmat([0;1],16,1);coded=[];
 if idx<=5
  f=idx-1;cfg=feval(['nrPUCCH' num2str(f) 'Config']);cfg.PRBSet=272;
  if f==0,cfg.SymbolAllocation=[12 2];b=1;else,cfg.SymbolAllocation=[0 14];end
  if f==2,cfg.NID0=17;else,cfg.HoppingID=17;end
  if f==2,cfg.PRBSet=269:272;cfg.SymbolAllocation=[0 2];b=[0;1;0;1;1;0;1];end
  if f==1,b=[0;1];end
  if f>=2,cfg.NID=17;cfg.RNTI=1;end
  if f==3,cfg.PRBSet=261:272;end
  if f==4,cfg.SpreadingFactor=2;cfg.OCCI=1;end
  di=nrPUCCHIndices(carrier,cfg);
  if f==0
   data=nrPUCCH0(b,[],[12 2],'normal',0,17,'neither',0,'disabled');
  elseif f==1
   data=nrPUCCH1(b,[],[0 14],'normal',0,17,'neither',0,'disabled',0);
  else
   sf=1;if f==4,sf=2;end
   coded=nrUCIEncode(b,2*numel(di)/sf);
   if f==2,data=nrPUCCH2(coded,17,1);elseif f==3,data=nrPUCCH3(coded,'QPSK',17,1,12);else,data=nrPUCCH4(coded,'QPSK',17,1,2,1);end
  end
  g(di)=data;
  if f>0,g(nrPUCCHDMRSIndices(carrier,cfg))=nrPUCCHDMRS(carrier,cfg);end
  module='pucch';
 elseif idx==6 || idx==7
  b=repmat([0;1],512,1);cfg=feval(['nr' name(3:end) 'Config']);
  cfg.PRBSet=0:272;cfg.SymbolAllocation=[0 12];cfg.Modulation='QPSK';cfg.RNTI=1;cfg.NID=17;
  cfg.DMRS.DMRSTypeAPosition=2;cfg.DMRS.DMRSAdditionalPosition=0;cfg.DMRS.NumCDMGroupsWithoutData=1;cfg.DMRS.NIDNSCID=17;
  if idx==6,cfg.TransformPrecoding=false;end
  [di,info]=feval(['nr' name(3:end) 'Indices'],carrier,cfg);
  coding=nrDLSCHInfo(1024,.5);blocks=nrCodeBlockSegmentLDPC(nrCRCEncode(b,coding.CRC),coding.BGN);
  coded=nrRateMatchLDPC(nrLDPCEncode(blocks,coding.BGN),info.G,0,'QPSK',1);
  g(di)=feval(['nr' name(3:end)],carrier,cfg,coded);
  g(feval(['nr' name(3:end) 'DMRSIndices'],carrier,cfg))=feval(['nr' name(3:end) 'DMRS'],carrier,cfg);
  module=lower(name(3:end));
 elseif idx==8
  co=nrCORESETConfig('FrequencyResources',ones(1,45),'Duration',2,'CCEREGMapping','noninterleaved');
  cfg=nrPDCCHConfig('NSizeBWP',273,'NStartBWP',0,'CORESET',co,'AggregationLevel',4,'CCEOffset',0,'RNTI',1,'DMRSScramblingID',17);
  cfg.SearchSpace.StartSymbolWithinSlot=0;[di,dm,pi]=nrPDCCHResources(carrier,cfg);
  coded=nrDCIEncode(b,1,432);g(di)=nrPDCCH(coded,17,1);g(pi)=dm;module='pdcch';
 elseif idx==9
  cfg=nrPRACHConfig('ConfigurationIndex',87,'SubcarrierSpacing',30,'ActivePRACHSlot',1,...
   'SequenceIndex',0,'PreambleIndex',7,'ZeroCorrelationZone',8,'FrequencyStart',261);
  for ns=0:159,cfg.NPRACHSlot=ns;symbols=nrPRACH(carrier,cfg);if ~isempty(symbols),break;end,end
  pg=nrPRACHGrid(carrier,cfg);pg(nrPRACHIndices(carrier,cfg))=symbols;
  [w,o]=nrPRACHOFDMModulate(carrier,cfg,pg,'Windowing',0);w=w(1:o.CyclicPrefixLengths(1)+2*o.Nfft);
  w=[w;zeros(32,1)];g=[];module='prach';b=7;
 else
  cfg=nrSRSConfig('CSRS',63,'BSRS',0,'BHop',0,'NumSRSPorts',1,'NumSRSSymbols',1,'SymbolStart',13,...
   'KTC',2,'KBarTC',0,'CyclicShift',0,'NRRC',0,'FrequencyStart',0,'NSRSID',0);
  g(nrSRSIndices(carrier,cfg))=nrSRS(carrier,cfg);module='srs';b=[];
 end
 if idx~=9,w=nrOFDMModulate(carrier,g,'Nfft',4096,'Windowing',0);end
 % Store full active-grid samples, but only deterministic 2048 waveform probes (not full waveform).
 gi=find(abs(g)>0);wi=unique(round(linspace(1,numel(w),min(2048,numel(w)))));
 r=struct('channel',name,'carrier_bandwidth_hz',100e6,'n_prbs',273,'scs_khz',30,'n_fft',4096,'sample_rate_hz',122880000,...
  'matlab_version',version,'toolbox',ver('5g'),'bits',b,'coded',coded,'grid_indices',gi-1,...
  'grid_real',real(g(gi)),'grid_imag',imag(g(gi)),'wave_indices',wi-1,'wave_real',real(w(wi)),'wave_imag',imag(w(wi)),...
  'wave_samples',numel(w),'wave_energy',sum(abs(w).^2));
 fid=fopen(fullfile(base,module,[name '_100MHz_30kHz_reference.json']),'w');fwrite(fid,jsonencode(r),'char');fclose(fid);
 fprintf('Exported %s 100MHz/30kHz\n',name);
end
end
