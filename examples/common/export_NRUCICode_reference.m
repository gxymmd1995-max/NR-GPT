function export_NRUCICode_reference
cases={};rng(123);
settings=[3 16;7 96;11 64;12 48;12 64;12 256;19 512;20 64;20 128;32 96;100 240;100 300;360 1088;1013 2304;1706 4096];
for k=1:size(settings,1)
 A=settings(k,1);E=settings(k,2);b=randi([0 1],A,1);x=nrUCIEncode(b,E);
 cases{end+1}=struct('A',A,'E',E,'bits',b,'encoded',x);
end
result=struct('matlab_version',version,'toolbox',ver('5g'),'cases',{cases});
fid=fopen(fullfile(fileparts(mfilename('fullpath')),'NRUCICode_reference.json'),'w');fwrite(fid,jsonencode(result),'char');fclose(fid);
end
