function export_NRCell_reference(outputFile)
%export_NRCell_reference 通过 MATLAB 5G Toolbox 生成独立对比数据。
% 仅使用 R15 配置；输出包含 78 个载波配置的尺寸和逐符号 OFDM 时序。
% 本函数不调用 Python，也不根据 Python 结果构造期望值。
% 参考：TS 38.211 V15.2.0 §4.2、§4.3、§4.4；nrCarrierConfig。
if nargin < 1
    % 与脚本同级；不依赖启动 MATLAB 时所在的工作目录。
    outputFile = fullfile(fileparts(mfilename('fullpath')), 'NRCell_reference.json');
end
scsValues = [15 30 60 120 240 60];
cpValues = {'normal','normal','normal','normal','normal','extended'};
cases = repmat(struct('input', struct(), 'expected', struct()), 0, 1);
rbValues = [52 1 275 10 11 21 22 42 43 85 86 170 171];
for i = 1:numel(scsValues)
    for variant = 1:numel(rbValues)
        carrier = nrCarrierConfig;
        carrier.SubcarrierSpacing = scsValues(i);
        carrier.CyclicPrefix = cpValues{i};
        if variant == 1
            carrier.NCellID = 42;
            carrier.NSizeGrid = 52;
            carrier.NStartGrid = 10;
            carrier.NFrame = 9;
            carrier.NSlot = 1;
        elseif variant == 2
            carrier.NCellID = 0;
            carrier.NSizeGrid = 1;
            carrier.NStartGrid = 0;
            carrier.NFrame = 0;
            carrier.NSlot = 0;
        elseif variant == 3
            carrier.NCellID = 1007;
            carrier.NSizeGrid = 275;
            carrier.NStartGrid = 2199;
            carrier.NFrame = 1023;
            carrier.NSlot = carrier.SlotsPerFrame - 1;
        else
            carrier.NCellID = 42;
            carrier.NSizeGrid = rbValues(variant);
            carrier.NStartGrid = 10;
            carrier.NFrame = 9;
            carrier.NSlot = 0;
        end
        grid = nrResourceGrid(carrier, 1);
        % 平台规则选择 Nfft，不使用 MATLAB 默认的 85% 占用率规则。
        nfft = max(128, 2^nextpow2(12 * carrier.NSizeGrid));
        ofdm = nrOFDMInfo(carrier, 'Nfft', nfft, 'Windowing', 0);
        cpSamples = ofdm.CyclicPrefixLengths;
        symbolSamples = ofdm.SymbolLengths;
        startSamples = [0 cumsum(symbolSamples(1:end-1))];
        tcPerSample = 1966080000 / ofdm.SampleRate;
        slotFirst = mod(carrier.NSlot, carrier.SlotsPerSubframe) * carrier.SymbolsPerSlot + 1;
        slotIndices = slotFirst:(slotFirst + carrier.SymbolsPerSlot - 1);
        item.input = struct('n_cell_id', carrier.NCellID, ...
            'subcarrier_spacing_khz', carrier.SubcarrierSpacing, ...
            'cyclic_prefix', carrier.CyclicPrefix, ...
            'n_size_grid', carrier.NSizeGrid, 'n_start_grid', carrier.NStartGrid, ...
            'n_frame', carrier.NFrame, 'n_slot', carrier.NSlot);
        item.expected = struct('symbols_per_slot', carrier.SymbolsPerSlot, ...
            'slots_per_subframe', carrier.SlotsPerSubframe, ...
            'slots_per_frame', carrier.SlotsPerFrame, ...
            'n_subcarriers', size(grid, 1), 'grid_symbols', size(grid, 2));
        item.expected.n_fft = ofdm.Nfft;
        item.expected.sample_rate_hz = ofdm.SampleRate;
        item.expected.tc_per_sample = tcPerSample;
        item.expected.cp_lengths_samples = cpSamples;
        item.expected.symbol_lengths_samples = symbolSamples;
        item.expected.symbol_start_samples = startSamples;
        item.expected.cp_lengths_tc = cpSamples * tcPerSample;
        item.expected.symbol_lengths_tc = symbolSamples * tcPerSample;
        item.expected.slot_cp_lengths_samples = cpSamples(slotIndices);
        item.expected.slot_symbol_lengths_samples = symbolSamples(slotIndices);
        item.expected.slot_start_sample = startSamples(slotFirst);
        item.expected.samples_per_slot = sum(symbolSamples(slotIndices));
        item.expected.samples_per_subframe = sum(symbolSamples);
        item.expected.samples_per_frame = 10 * sum(symbolSamples);
        cases(end + 1) = item; %#ok<AGROW>
    end
end
result.matlab_version = version;
result.toolbox = ver('5g');
result.generated_at = char(datetime('now', 'TimeZone', 'UTC', 'Format', 'yyyy-MM-dd''T''HH:mm:ssXXX'));
result.spec_baseline = '3GPP TS 38.211 V15.2.0 (R15 subset)';
result.fft_policy = 'max(128, 2^ceil(log2(12*NSizeGrid))); explicit Nfft, Windowing=0, no resampling';
result.cases = cases;
fid = fopen(outputFile, 'w', 'n', 'UTF-8');
assert(fid >= 0, 'Cannot open output file: %s', outputFile);
closer = onCleanup(@() fclose(fid));
fprintf(fid, '%s\n', jsonencode(result, 'PrettyPrint', true));
fprintf('Exported %d MATLAB reference cases to %s\n', numel(cases), outputFile);
end
