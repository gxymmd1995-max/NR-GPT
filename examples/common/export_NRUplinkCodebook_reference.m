function export_NRUplinkCodebook_reference(outputFile)
% R15 1/2/4端口全部72个矩阵，独立调用nrPUSCHCodebook，关闭变换预编码。
% MATLAB返回[层,端口]，以非共轭转置恢复38.211 V15.2.0 §6.3.1.5的[端口,层]。
if nargin<1
    outputFile=fullfile(fileparts(mfilename('fullpath')),'NRUplinkCodebook_reference.json');
end
specs=[1 1 1; 2 1 6; 2 2 3; 4 1 28; 4 2 22; 4 3 7; 4 4 5];
cases=repmat(struct('n_ports',0,'rank',0,'tpmi',0,'real',[],'imag',[]),0,1);
for s=1:size(specs,1)
    for tpmi=0:specs(s,3)-1
        p=specs(s,1); rank=specs(s,2);
        w=nrPUSCHCodebook(rank,p,tpmi,false).';
        % Python矩阵C-order为先列后行，MATLAB将W.'按列展平得到同序。
        values=w.';
        cases(end+1)=struct('n_ports',p,'rank',rank,'tpmi',tpmi, ...
            'real',real(values(:)),'imag',imag(values(:))); %#ok<AGROW>
    end
end
result.matlab_version=version; result.toolbox=ver('5g');
result.generated_at=char(datetime('now','TimeZone','UTC','Format','yyyy-MM-dd''T''HH:mm:ssXXX'));
result.spec_baseline='TS 38.211 V15.2.0 section 6.3.1.5 tables 1,3,4,5,6,7';
result.cases=cases;
fid=fopen(outputFile,'w','n','UTF-8');assert(fid>=0);closer=onCleanup(@()fclose(fid));
fprintf(fid,'%s\n',jsonencode(result,'PrettyPrint',true));
fprintf('Exported %d actual PUSCH codebook matrices\n',numel(cases));
end
