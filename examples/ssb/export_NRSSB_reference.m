function export_NRSSB_reference
cases={};id=0;
for id=1:25
   m=min(id,24)-1;lms=[4 8 64];lm=lms(floor(m/8)+1);hf=floor(mod(m,8)/4);sfn=2*mod(m,4);
   nsize=24;nfft=512;if id==25,nsize=273;nfft=4096;lm=8;end
   scs=30;if lm==64,scs=120;end
   pcis=[0 1 2 1007];pci=pcis(mod(id-1,4)+1);ix=lm-1;kssb=23;
   mib=mod((0:23).'+id,2);offset=kssb;if lm==64,offset=ix;end
   coded=nrBCH(mib,sfn,hf,lm,offset,pci);
   local=zeros(240,4);local(nrPSSIndices)=nrPSS(pci);local(nrSSSIndices)=nrSSS(pci);
   v=mod(ix,8);if lm==4,v=mod(ix,4);end
   local(nrPBCHIndices(pci))=nrPBCH(coded,pci,v);
   ibar=mod(ix,8);if lm==4,ibar=ix+4*hf;end
   local(nrPBCHDMRSIndices(pci))=nrPBCHDMRS(pci,ibar);
   carrier=nrCarrierConfig('NCellID',pci,'NSizeGrid',nsize,'SubcarrierSpacing',scs);
   grid=nrResourceGrid(carrier);grid(25:264,3:6)=local;
   wave=nrOFDMModulate(carrier,grid,'Nfft',nfft,'Windowing',0);
   cases{end+1}=struct('scs',scs,'n_size_grid',nsize,'pci',pci,'lmax',lm,'ssb_index',ix,'half_frame',hf,'k_ssb',kssb,...
    'sfn_lsb',sfn,'mib',mib,'coded',coded,'grid_real',real(grid(:)),'grid_imag',imag(grid(:)),...
    'wave_real',real(wave),'wave_imag',imag(wave));
end
result=struct('matlab_version',version,'toolbox',ver('5g'),'cases',{cases});
fid=fopen(fullfile(fileparts(mfilename('fullpath')),'NRSSB_reference.json'),'w');fwrite(fid,jsonencode(result),'char');fclose(fid);
fprintf('Exported %d actual SSB/BCH cases\n',numel(cases));
end
