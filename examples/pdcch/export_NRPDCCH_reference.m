function export_NRPDCCH_reference
rng(42);cases={};
for al=[1 2 4 8 16]
 for variant=0:2
  c=nrCarrierConfig('NSizeGrid',96,'NStartGrid',12,'SubcarrierSpacing',30,'NSlot',3);
  cr=nrCORESETConfig('FrequencyResources',ones(1,16),'Duration',variant+1,...
    'CCEREGMapping','noninterleaved');
  if variant==1,cr.CCEREGMapping='interleaved';cr.REGBundleSize=2;cr.InterleaverSize=3;cr.ShiftIndex=17;end
  p=nrPDCCHConfig('NStartBWP',12,'NSizeBWP',96,'CORESET',cr,'RNTI',4321,...
    'DMRSScramblingID',271,'AggregationLevel',al,'CCEOffset',0);
  p.SearchSpace.StartSymbolWithinSlot=1;
  [di,dm,pi]=nrPDCCHResources(c,p);E=108*al;
  A=32;if variant==2,A=12;elseif al>=2,A=140;end
  b=randi([0 1],A,1);coded=nrDCIEncode(b,4321,E);
  grid=nrResourceGrid(c);grid(di)=nrPDCCH(coded,271,4321);grid(pi)=dm;
  wave=nrOFDMModulate(c,grid,'Nfft',2048,'Windowing',0);
  cases{end+1}=struct('al',al,'variant',variant,'A',A,'bits',b,'coded',coded,...
   'grid_real',real(grid(:)),'grid_imag',imag(grid(:)),'wave_real',real(wave),'wave_imag',imag(wave));
 end
end
result=struct('matlab_version',version,'toolbox',ver('5g'),'cases',{cases});
fid=fopen(fullfile(fileparts(mfilename('fullpath')),'NRPDCCH_reference.json'),'w');fwrite(fid,jsonencode(result),'char');fclose(fid);
fprintf('Exported %d actual PDCCH cases\n',numel(cases));
end
