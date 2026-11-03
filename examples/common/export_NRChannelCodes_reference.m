function export_NRChannelCodes_reference
cases={};
for N=[64 128 256 512 1024]
 K=N/2; b=mod((0:K-1).'+floor(N/64),2);
 x=nrPolarEncode(b,N,10,false);
 cases{end+1}=struct('kind','polar','N',N,'K',K,'bits',b,'encoded',x);
end
for bg=1:2
 for Z=[2 8 16]
 K=(22*(bg==1)+10*(bg==2))*Z; b=mod((0:K-1).',2);
 x=nrLDPCEncode(b,bg);
 cases{end+1}=struct('kind','ldpc','bg',bg,'Z',Z,'bits',b,'encoded',x);
 end
end
% Classical RM independent MATLAB polynomial evaluation, not a Toolbox NR codec.
for r=0:2
 m=4; terms={[]};
 for degree=1:r
 combos=nchoosek(1:m,degree);
 for j=1:size(combos,1),terms{end+1}=combos(j,:);end
 end
 G=ones(numel(terms),2^m);
 for j=1:numel(terms)
 for n=0:2^m-1
 for v=terms{j},G(j,n+1)=G(j,n+1)*bitget(n,v);end
 end
 end
 b=mod((0:numel(terms)-1).',2);x=mod(G.'*b,2);
 cases{end+1}=struct('kind','rm','r',r,'m',m,'bits',b,'encoded',x);
end
result=struct('matlab_version',version,'toolbox',ver('5g'),'cases',{cases});
fid=fopen(fullfile(fileparts(mfilename('fullpath')),'NRChannelCodes_reference.json'),'w');fwrite(fid,jsonencode(result),'char');fclose(fid);
end

