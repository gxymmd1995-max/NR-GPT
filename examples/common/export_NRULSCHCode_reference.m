function export_NRULSCHCode_reference
% Actual single-code-block UL-SCH CRC16/24A, BG1/2 and full-buffer RV rate matching.
settings=[16 .5 2 0;160 .5 4 2;256 .5 8 1;512 .8 6 3;4000 .8 4 2];cases={};rng(123);
mods={'QPSK','16QAM','64QAM','256QAM'};
for i=1:size(settings,1)
 A=settings(i,1);rate=settings(i,2);qm=settings(i,3);rv=settings(i,4);
 info=nrDLSCHInfo(A,rate);b=randi([0 1],A,1);tb=nrCRCEncode(b,info.CRC);
 blocks=nrCodeBlockSegmentLDPC(tb,info.BGN);encoded=nrLDPCEncode(blocks,info.BGN);
 E=ceil(2*size(encoded,1)/qm)*qm;coded=nrRateMatchLDPC(encoded,E,rv,mods{qm/2},1);
 cases{end+1}=struct('A',A,'rate',rate,'qm',qm,'rv',rv,'E',E,'bg',info.BGN,'Z',info.Zc,'bits',b,'coded',coded);
end
result=struct('matlab_version',version,'toolbox',ver('5g'),'cases',{cases});
fid=fopen(fullfile(fileparts(mfilename('fullpath')),'NRULSCHCode_reference.json'),'w');fwrite(fid,jsonencode(result),'char');fclose(fid);
end
