function export_NRGrid_reference(outputFile)
%export_NRGrid_reference 独立生成 18 组单时隙网格及索引映射参考。
% 原文依据：TS 38.211 V15.2.0 §4.3.2、§4.4.1–§4.4.5。
% nrResourceGrid 提供真实空网格；测试程序另外管理标签占用并用 sub2ind 映射。
% 不实现或模拟任何具体物理信道序列，不调用 Python。
if nargin < 1
    outputFile = fullfile(fileparts(mfilename('fullpath')), 'NRGrid_reference.json');
end
scsValues = [15 30 60 120 240 60];
cpValues = {'normal','normal','normal','normal','normal','extended'};
rbValues = [1 24 52];
portValues = [1 2 4];
cases = repmat(struct('input', struct(), 'selection', struct(), 'expected', struct()), 0, 1);
for i = 1:numel(scsValues)
    for j = 1:numel(rbValues)
        carrier = nrCarrierConfig;
        carrier.SubcarrierSpacing = scsValues(i);
        carrier.CyclicPrefix = cpValues{i};
        carrier.NSizeGrid = rbValues(j);
        carrier.NStartGrid = 10;
        nPorts = portValues(j);
        grid = nrResourceGrid(carrier, nPorts);
        bwpStart = 10 + min(2, carrier.NSizeGrid - 1);
        bwpSize = min(4, carrier.NSizeGrid - (bwpStart - 10));
        prbs = unique([0 min(1, bwpSize - 1) bwpSize - 1], 'stable');
        symbols = [0 carrier.SymbolsPerSlot - 1];
        ports = 0:(nPorts - 1);
        coordinates = zeros(0, 3);
        for p = ports
            for l = symbols
                for rb = prbs
                    for sc = 0:11
                        k = 12 * (bwpStart - carrier.NStartGrid + rb) + sc;
                        coordinates(end + 1, :) = [p l k]; %#ok<AGROW>
                    end
                end
            end
        end
        count = size(coordinates, 1);
        values = (1:count).' / 16 - 1j * (count:-1:1).' / 32;
        values(1) = 0; % 零值仍是已映射 RE，不能按振幅判断是否占用。
        linearIndices = sub2ind([size(grid,1), size(grid,2), nPorts], ...
            coordinates(:,3)+1, coordinates(:,2)+1, coordinates(:,1)+1);
        grid(linearIndices) = values;
        occupied = false(size(grid));
        occupied(linearIndices) = true;
        reserve = [0 1 size(grid,1)-1];
        reserveLinear = sub2ind([size(grid,1), size(grid,2), nPorts], reserve(3)+1, reserve(2)+1, reserve(1)+1);
        occupied(reserveLinear) = true;
        flat = grid(:);
        weights = (1:numel(flat)).';
        item.input = struct('subcarrier_spacing_khz', carrier.SubcarrierSpacing, ...
            'cyclic_prefix', carrier.CyclicPrefix, 'n_size_grid', carrier.NSizeGrid, ...
            'n_start_grid', carrier.NStartGrid, 'bwp_start', bwpStart, 'bwp_size', bwpSize);
        item.selection = struct('n_ports', nPorts, 'prbs', prbs, 'symbols', symbols, 'ports', ports);
        item.expected = struct('python_shape', [nPorts size(grid,2) size(grid,1)], ...
            'matlab_shape', [size(grid,1) size(grid,2) nPorts], ...
            'indices', coordinates, 'linear_indices_1based', linearIndices, ...
            'values_real', real(grid(linearIndices)), 'values_imag', imag(grid(linearIndices)), ...
            'reserve_index', reserve, 'occupied_re_count', nnz(occupied), ...
            'total_re_count', numel(grid), 'nonzero_count', nnz(grid), ...
            'sum_real', sum(real(flat)), 'sum_imag', sum(imag(flat)), ...
            'weighted_real', sum(real(flat).*weights), 'weighted_imag', sum(imag(flat).*weights));
        cases(end + 1) = item; %#ok<AGROW>
    end
end
result.matlab_version = version;
result.toolbox = ver('5g');
result.generated_at = char(datetime('now', 'TimeZone', 'UTC', 'Format', 'yyyy-MM-dd''T''HH:mm:ssXXX'));
result.spec_baseline = '3GPP TS 38.211 V15.2.0 (R15 grid subset)';
result.axis_note = 'MATLAB [subcarrier,symbol,port]; Python [port,symbol,subcarrier]; zero-based coordinates';
result.cases = cases;
fid = fopen(outputFile, 'w', 'n', 'UTF-8');
assert(fid >= 0, 'Cannot open output file: %s', outputFile);
closer = onCleanup(@() fclose(fid));
fprintf(fid, '%s\n', jsonencode(result, 'PrettyPrint', true));
fprintf('Exported %d independent grid cases to %s\n', numel(cases), outputFile);
end
