function export_NRPRACH_reference
% Actual R15-compatible PRACH symbols and OFDM, no Python vectors used.
formats={'0','1','2','3','A1','A2','A3','B1','B2','B3','B4','C0','C2'};
t=nrPRACHConfig.Tables.ConfigurationsFR1PairedSUL;cases={};
for f=1:numel(formats)
 fmt=formats{f};idx=find(strcmp(t.PreambleFormat,fmt),1);ti=0;
 if isempty(idx)
  idx=find(strcmp(t.PreambleFormat,['A' fmt(2) '/B' fmt(2)]),1);
  ti=t.NumTimeOccasions(idx)-1;
 end
 variants=0:1;if f>4,variants=0:3;end
 for variant=variants
  ra=15;if f<=3,ra=1.25;elseif f==4,ra=5;elseif variant==1,ra=30;end
  ul=30;fr='FR1';duplex='FDD';table=t;
  if variant>=2
   fr='FR2';duplex='TDD';ul=120;ra=60*2^(variant-2);table=nrPRACHConfig.Tables.ConfigurationsFR2;
   idx=find(strcmp(table.PreambleFormat,fmt),1);ti=0;
   if isempty(idx),idx=find(strcmp(table.PreambleFormat,['A' fmt(2) '/B' fmt(2)]),1);ti=table.NumTimeOccasions(idx)-1;end
  end
  c=nrCarrierConfig('NSizeGrid',52,'SubcarrierSpacing',ul);
  p=nrPRACHConfig('FrequencyRange',fr,'DuplexMode',duplex,'ConfigurationIndex',table.ConfigurationIndex(idx),'SubcarrierSpacing',ra,...
     'SequenceIndex',mod(837-17*f,138),'PreambleIndex',63*mod(variant,2),'ZeroCorrelationZone',mod(1+11*variant,16),...
     'FrequencyStart',1+variant,'TimeIndex',ti);
  if ra==30 || ra==120,p.ActivePRACHSlot=1;end
  for ns=0:159
   p.NPRACHSlot=ns;[s,si]=nrPRACH(c,p);
   if ~isempty(s),break;end
  end
  assert(~isempty(s));g=nrPRACHGrid(c,p);ind=nrPRACHIndices(c,p);g(ind)=s;
  [wave,o]=nrPRACHOFDMModulate(c,p,g,'Windowing',0);
  % Only export selected occasion CP + active repeats; unused RO/frame padding is excluded.
  occupied=find(any(abs(g)>0,1));first=occupied(1);last=occupied(end);
  start=o.OffsetLength+sum(o.SymbolLengths(1:first-1));cp=o.CyclicPrefixLengths(first);
  active=cp+(last-first+1)*o.Nfft;
  selected=wave(start+(1:active),:);
  origin=0;if ra==30,origin=o.SampleRate/2000;elseif ra==120,origin=o.SampleRate/8000;end
  if strcmp(fr,'FR2'),origin=origin+mod(p.NPRACHSlot,2)*o.SampleRate/4000;end
  cases{end+1}=struct('format',fmt,'ra_scs',ra,'root',p.SequenceIndex,'preamble',p.PreambleIndex,...
    'zcz',p.ZeroCorrelationZone,'frequency_start',p.FrequencyStart,'configuration_index',p.ConfigurationIndex,...
    'prach_slot',p.NPRACHSlot,'time_index',ti,'frequency_range',fr,'cell_scs',ul,'n_size',52,'sample_rate',o.SampleRate,...
    'time_origin',origin,'fft',o.Nfft,'cp',cp,'start',start,'repetitions',last-first+1,'sequence_info',si,...
    'symbols_real',real(s),'symbols_imag',imag(s),'wave_real',real(selected),'wave_imag',imag(selected));
 end
end
edges={};c=nrCarrierConfig('NSizeGrid',52,'SubcarrierSpacing',30);
for long=[true false]
 for z=0:15
  ci=27;ra=1.25;root=837;if ~long,ci=87;ra=15;root=137;end
  p=nrPRACHConfig('ConfigurationIndex',ci,'SubcarrierSpacing',ra,'SequenceIndex',root,...
   'ZeroCorrelationZone',z,'PreambleIndex',63);
  for ns=0:159,p.NPRACHSlot=ns;[sym,si]=nrPRACH(c,p);if ~isempty(sym),break;end,end
  edges{end+1}=struct('format',p.Format,'ra_scs',ra,'root',root,'zcz',z,'preamble',63,...
    'sequence_info',si,'symbols_real',real(sym),'symbols_imag',imag(sym));
 end
end
result=struct('matlab_version',version,'toolbox',ver('5g'),'cases',{cases},'sequence_cases',{edges});
fid=fopen(fullfile(fileparts(mfilename('fullpath')),'NRPRACH_reference.json'),'w');
fwrite(fid,jsonencode(result),'char');fclose(fid);fprintf('Exported %d actual PRACH cases\n',numel(cases));
end
