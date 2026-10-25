function export_NRSRS_reference(outputFile)
%export_NRSRS_reference 独立调用 nrSRS/nrSRSIndices 生成 R15 SRS 参考。
% 基线：TS 38.211 V15.2.0 §5.2、§6.4.1.4；38.331 V15.2.1 §6.3.2。
% 不调用 Python；每组保留输入、全部复数向量、全部零起始 [p,l,k] 坐标。
% MATLAB 的后续版本扩展显式关闭；逻辑端口数量与物理天线数量独立。
if nargin < 1
    outputFile = fullfile(fileparts(mfilename('fullpath')), 'NRSRS_reference.json');
end
base.cell = struct('n_cell_id', 42, 'subcarrier_spacing_khz', 30, 'cyclic_prefix', 'normal', ...
    'n_size_grid', 275, 'n_start_grid', 10, 'bwp_start', 10, 'bwp_size', 275, ...
    'n_frame', 0, 'n_slot', 0, 'duplex_mode', 'TDD', 'n_tx_antennas', 4, 'n_rx_antennas', 2);
base.n_ports = 1; base.n_symbols = 1; base.start_position = 0;
base.c_srs = 0; base.b_srs = 0; base.b_hop = 0;
base.k_tc = 2; base.comb_offset = 0; base.cyclic_shift = 0;
base.frequency_shift = 0; base.frequency_position = 0; base.sequence_id = 0;
base.group_seq_hopping = 'neither'; base.repetition = 1;
base.resource_type = 'periodic'; base.periodicity = 1; base.slot_offset = 0; base.enabled = true;
inputs = repmat(base, 0, 1);
% 全部带宽表：64行×4层级×两种comb，含 n_RRC 模偏移。
for c = 0:63
    for b = 0:3
        for ktc = [2 4]
            x = base; x.c_srs = c; x.b_srs = b; x.b_hop = 3;
            x.k_tc = ktc; x.comb_offset = ktc-1;
            x.cyclic_shift = 2*ktc+3; x.frequency_position = 67; x.sequence_id = mod(c,30);
            inputs(end+1) = x; %#ok<AGROW>
        end
    end
end
% 短序列全部30组，以及多端口循环移位/特殊梳齿。
ports = [1 2 4];
for u = 0:29
    for ktc = [2 4]
        x = base; x.cell.n_size_grid = 24; x.cell.bwp_start = 12; x.cell.bwp_size = 20;
        x.frequency_shift = 2; x.sequence_id = u; x.k_tc = ktc;
        x.n_ports = ports(mod(u,3)+1); x.n_symbols = ports(mod(u+1,3)+1);
        x.start_position = x.n_symbols; x.cyclic_shift = mod(u,2*ktc+4);
        inputs(end+1) = x; %#ok<AGROW>
    end
end
scs = [15 30 60 120 240 60]; cp = {'normal','normal','normal','normal','normal','extended'};
modes = {'neither','groupHopping','sequenceHopping'};
for i = 1:6
    for mode = 1:3
        for ktc = [2 4]
            x = base; x.cell.subcarrier_spacing_khz = scs(i); x.cell.cyclic_prefix = cp{i};
            x.cell.n_size_grid = 52; x.cell.bwp_start = 14; x.cell.bwp_size = 44;
            x.cell.n_frame = 7; x.cell.n_slot = 10*(scs(i)/15)-1;
            x.n_ports = 4; x.n_symbols = 4; x.start_position = 5;
            x.c_srs = 7; x.frequency_shift = 6; x.sequence_id = 1023;
            x.k_tc = ktc; x.cyclic_shift = 2*ktc+3; x.comb_offset = ktc-1;
            x.group_seq_hopping = modes{mode};
            inputs(end+1) = x; %#ok<AGROW>
        end
    end
end
% 偶/奇 N_b、多层 F_b、帧内/跨帧计数、重复因子与非周期复位。
for c = 1:63
    for b = 1:3
        x = base; x.c_srs = c; x.b_srs = b; x.b_hop = mod(c,b);
        x.n_ports = ports(mod(c,3)+1); x.n_symbols = 4; x.start_position = 4;
        x.repetition = ports(mod(c+b,3)+1); x.frequency_position = 67;
        x.cell.n_frame = mod(c,2)*1023; x.cell.n_slot = mod(c,20);
        x.k_tc = 2+2*mod(c,2); x.cyclic_shift = 2*x.k_tc+3;
        x.periodicity = 2; x.slot_offset = mod(x.cell.n_slot,2);
        x.group_seq_hopping = modes{mod(c,3)+1}; x.sequence_id = 31+c;
        if mod(c,3) == 0
            x.resource_type = 'aperiodic'; x.periodicity = 1; x.slot_offset = 0;
        elseif mod(c,3) == 1
            x.resource_type = 'semi-persistent';
        end
        inputs(end+1) = x; %#ok<AGROW>
    end
end
% R15 的所有周期，包含候选/非候选、enabled=off、跨SFN边界。
periods = [1 2 4 5 8 10 16 20 32 40 64 80 160 320 640 1280 2560];
for period = periods
    for delta = [0 1]
        x = base; x.periodicity = period; x.slot_offset = period-1;
        absolute = 2*period + period-1 + delta;
        x.cell.n_frame = floor(absolute/20); x.cell.n_slot = mod(absolute,20);
        x.enabled = ~(period==1 && delta==1);
        inputs(end+1) = x; %#ok<AGROW>
    end
end
x = base; x.resource_type = 'aperiodic'; x.enabled = false; inputs(end+1) = x;
cases = repmat(struct('input',struct(),'expected',struct()),0,1);
for i = 1:numel(inputs)
    x = inputs(i); carrier = nrCarrierConfig;
    carrier.NCellID = x.cell.n_cell_id; carrier.SubcarrierSpacing = x.cell.subcarrier_spacing_khz;
    carrier.CyclicPrefix = x.cell.cyclic_prefix; carrier.NSizeGrid = x.cell.n_size_grid;
    carrier.NStartGrid = x.cell.n_start_grid; carrier.NFrame = x.cell.n_frame;
    % NFrame 与帧内 NSlot 成对输入；避免把帧号再次加入 NSlot 导致重复累计。
    carrier.NSlot = x.cell.n_slot;
    srs = nrSRSConfig;
    srs.NumSRSPorts = x.n_ports; srs.NumSRSSymbols = x.n_symbols;
    srs.SymbolStart = carrier.SymbolsPerSlot - 1 - x.start_position;
    srs.CSRS = x.c_srs; srs.BSRS = x.b_srs; srs.BHop = x.b_hop;
    srs.KTC = x.k_tc; srs.KBarTC = x.comb_offset; srs.CyclicShift = x.cyclic_shift;
    srs.FrequencyStart = x.frequency_shift; srs.NRRC = x.frequency_position;
    srs.NSRSID = x.sequence_id; srs.GroupSeqHopping = x.group_seq_hopping;
    srs.Repetition = x.repetition; srs.ResourceType = x.resource_type;
    if ~x.enabled
        srs.SRSPeriod = 'off';
    elseif strcmp(x.resource_type,'aperiodic')
        srs.SRSPeriod = 'on';
    else
        srs.SRSPeriod = [x.periodicity x.slot_offset];
    end
    srs.SRSPositioning = false; srs.FrequencyScalingFactor = 1; srs.StartRBIndex = 0;
    srs.EnableStartRBHopping = false; srs.EnableEightPortTDM = false;
    srs.CyclicShiftHopping = false; srs.CombOffsetHopping = false;
    srs.HoppingFinerGranularity = false; srs.HoppingWithRepetition = false;
    [symbols, seqInfo] = nrSRS(carrier,srs);
    [indices, indexInfo] = nrSRSIndices(carrier,srs,'IndexStyle','subscript','IndexBase','0based');
    coordinates = double(indices(:,[3 2 1]));
    grid = nrResourceGrid(carrier,x.n_ports);
    values = symbols(:)/sqrt(x.n_ports); % beta=1；38.211 V15.2.0 §6.4.1.4.3。
    if ~isempty(coordinates)
        linear = sub2ind([size(grid,1),size(grid,2),x.n_ports], ...
            coordinates(:,3)+1,coordinates(:,2)+1,coordinates(:,1)+1);
        grid(linear) = values;
    end
    e.active = ~isempty(symbols); e.indices = coordinates;
    e.sequence_shape = [size(symbols,1) x.n_ports];
    e.symbols_real = real(symbols(:)); e.symbols_imag = imag(symbols(:));
    e.seq_group = seqInfo.SeqGroup; e.n_seq = seqInfo.NSeq; e.alpha = seqInfo.Alpha;
    e.sequence_length = seqInfo.SeqLength; e.k0 = indexInfo.SubcarrierOffset;
    e.frequency_indices = indexInfo.FreqIndex; e.occupied_re_count = numel(values);
    e.grid_energy = sum(abs(grid(:)).^2);
    e.grid_weighted_real = sum(real(grid(:)).*(1:numel(grid)).');
    e.grid_weighted_imag = sum(imag(grid(:)).*(1:numel(grid)).');
    cases(end+1) = struct('input',x,'expected',e); %#ok<AGROW>
end
result.matlab_version = version; result.toolbox = ver('5g');
result.generated_at = char(datetime('now','TimeZone','UTC','Format','yyyy-MM-dd''T''HH:mm:ssXXX'));
result.spec_baseline = 'TS 38.211 V15.2.0; TS 38.331 V15.2.1';
result.note = 'Independent nrSRS + nrSRSIndices + nrResourceGrid; raw symbols then beta=1/sqrt(P) grid scaling; zero-based [p,l,k]; complex vectors flattened port-first';
result.cases = cases;
fid = fopen(outputFile,'w','n','UTF-8'); assert(fid>=0,'Cannot open output file');
closer = onCleanup(@() fclose(fid));
fprintf(fid,'%s\n',jsonencode(result));
fprintf('Exported %d independent SRS cases to %s\n',numel(cases),outputFile);
end
