function export_NROFDM_reference(outputFile)
% 真实nrOFDMModulate/nrOFDMDemodulate/nrOFDMInfo独立参考，固定R15 numerology。
% 不使用默认FFT或默认加窗；保留全部时域复数样点及独立扰动后的解调输出。
if nargin<1,outputFile=fullfile(fileparts(mfilename('fullpath')),'NROFDM_reference.json');end
scs=[15 30 60 120 240 60];cp={'normal','normal','normal','normal','normal','extended'};
cases=repmat(struct('input',struct(),'expected',struct()),0,1);
for id=0:27
    i=mod(floor(id/4),6)+1; rb=1;
    if id>=24,i=mod(id-24,6)+1;rb=24;end
    slot=mod(floor(id/2),2); fc=3500000123*mod(id,2); ports=1+mod(id,2);
    carrier=nrCarrierConfig('NSizeGrid',rb,'NStartGrid',10,'SubcarrierSpacing',scs(i),'CyclicPrefix',cp{i},'NSlot',slot);
    nfft=max(128,2^nextpow2(12*rb));L=carrier.SymbolsPerSlot;
    values=exp(1j*pi/2*mod((0:12*rb*L*ports-1).',4));grid=reshape(values,12*rb,L,ports);
    [wave,info]=nrOFDMModulate(carrier,grid,'Nfft',nfft,'Windowing',0,'CarrierFrequency',fc);
    % 独立接收输入包含确定性非OFDM扰动，避免只验证自身调制/解调闭环。
    probe=wave+.002*reshape(sin((1:numel(wave))*.13)+1j*cos((1:numel(wave))*.07),size(wave));
    fraction=[0 .5 1];demod=repmat(struct('cp_fraction',0,'real',[],'imag',[]),0,1);
    for f=fraction
        recovered=nrOFDMDemodulate(carrier,probe,'Nfft',nfft,'CarrierFrequency',fc,'CyclicPrefixFraction',f);
        demod(end+1)=struct('cp_fraction',f,'real',real(recovered(:)),'imag',imag(recovered(:))); %#ok<AGROW>
    end
    start=mod(slot,carrier.SlotsPerSubframe)*L;
    input.cell=struct('n_size_grid',rb,'n_start_grid',10,'subcarrier_spacing_khz',scs(i),'cyclic_prefix',cp{i},'n_slot',slot);
    input.carrier_frequency_hz=uint64(fc);input.n_branches=ports;
    input.grid_real=real(grid(:));input.grid_imag=imag(grid(:));
    input.probe_real=real(probe(:));input.probe_imag=imag(probe(:));
    expected.wave_real=real(wave(:));expected.wave_imag=imag(wave(:));expected.n_samples=size(wave,1);
    expected.symbol_phases=info.SymbolPhases(start+(1:L));expected.demod=demod;
    expected.cp_lengths=info.CyclicPrefixLengths(start+(1:L));
    cases(end+1)=struct('input',input,'expected',expected); %#ok<AGROW>
end
result.matlab_version=version;result.toolbox=ver('5g');
result.generated_at=char(datetime('now','TimeZone','UTC','Format','yyyy-MM-dd''T''HH:mm:ssXXX'));
result.spec_baseline='TS38.211 V15.2.0 sections5.3.1/5.4; single numerology; Windowing0; explicit Nfft';result.cases=cases;
fid=fopen(outputFile,'w','n','UTF-8');assert(fid>=0);closer=onCleanup(@()fclose(fid));
fprintf(fid,'%s\n',jsonencode(result));fprintf('Exported %d actual OFDM/phase cases\n',numel(cases));
end
