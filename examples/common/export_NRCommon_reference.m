function export_NRCommon_reference(outputFile)
%export_NRCommon_reference 使用真正 nrPRBS 独立生成Gold比特，固定R15 §5.2.1。
% 输出包含全部输入和二进制比特；offset从标准Gold输出c(0)开始计数。
if nargin < 1
    outputFile = fullfile(fileparts(mfilename('fullpath')), 'NRCommon_reference.json');
end
cases = repmat(struct('input',struct(),'bits',[]),0,1);
lengths = [1 31 128 0]; offsets = [0 17 1600 5];
for seed = [0 1 42 1023 2^31-1]
    for i = 1:numel(lengths)
        count = lengths(i); offset = offsets(i);
        allBits = nrPRBS(seed,offset+max(count,1));
        bits = allBits(offset+(1:count));
        % uint32 保证最大31bit种子以JSON整数编码，不被double格式写成科学计数法。
        cases(end+1) = struct('input',struct('c_init',uint32(seed),'length',count,'offset',offset), ...
                              'bits',double(bits)); %#ok<AGROW>
    end
end
result.matlab_version = version; result.toolbox = ver('5g');
result.generated_at = char(datetime('now','TimeZone','UTC','Format','yyyy-MM-dd''T''HH:mm:ssXXX'));
result.spec_baseline = 'TS 38.211 V15.2.0 section 5.2.1';
result.note = 'Independent MATLAB nrPRBS binary vectors; SRS u/v reference remains in examples/srs/NRSRS_reference.json';
result.cases = cases;
fid = fopen(outputFile,'w','n','UTF-8'); assert(fid>=0,'Cannot open output file');
closer = onCleanup(@() fclose(fid));
fprintf(fid,'%s\n',jsonencode(result,'PrettyPrint',true));
fprintf('Exported %d independent Gold cases to %s\n',numel(cases),outputFile);
end
