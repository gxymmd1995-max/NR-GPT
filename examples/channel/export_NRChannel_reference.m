function export_NRChannel_reference(outputFile)
% 原生MATLAB独立TA移位、CFO与显式复高斯向量。TA换算固定38.213 V15.3.0 §4.2。
% 噪声保存实际randn向量，避免要求Python与MATLAB使用相同PRNG内部实现。
if nargin<1,outputFile=fullfile(fileparts(mfilename('fullpath')),'NRChannel_reference.json');end
cases=repmat(struct('input',struct(),'expected',struct()),0,1);
for id=0:23
    rng(8100+id,'twister');rb=1+51*mod(id,2);scs=15*2^mod(id,5);N=37+219*mod(id,2);B=2;
    carrier=nrCarrierConfig('NSizeGrid',rb,'SubcarrierSpacing',scs);nfft=max(128,2^nextpow2(12*rb));fs=nfft*scs*1000;
    x=(randn(N,B)+1j*randn(N,B))/sqrt(2);standard=(randn(N,B)+1j*randn(N,B))/sqrt(2);
    shifts=[-7 0 5 N];ta=shifts(mod(id,4)+1);shifted=complex(zeros(N,B));
    if ta>=0,shifted(1:N-ta,:)=x(ta+1:end,:);else,shifted(1-ta:end,:)=x(1:N+ta,:);end
    offsets=[-1234 0 8765];freq=offsets(mod(id,3)+1);start=13+id*10000;phase=.37;
    rotated=shifted.*exp(1j*(phase+2*pi*freq*(start+(0:N-1).')/fs));
    snrDb=-5+5*mod(id,8);power=mean(abs(rotated).^2,1)*10^(-snrDb/10);noise=standard.*sqrt(power);received=rotated+noise;
    command=mod(id*7,64);initial=mod(id,2)==1;
    if initial,command=mod(id*179,3847);end
    tcDelta=(command-31*(~initial))*16*64/2^mod(id,5);samples=tcDelta/(1966080000/fs);
    input.cell=struct('n_size_grid',rb,'subcarrier_spacing_khz',scs);
    input.n_branches=B;input.n_samples=N;input.ta_samples=ta;input.frequency_offset_hz=freq;
    input.initial_phase_rad=phase;input.start_sample=start;input.snr_db=snrDb;input.seed=8100+id;
    input.real=real(x(:));input.imag=imag(x(:));input.standard_real=real(standard(:));input.standard_imag=imag(standard(:));
    input.command=command;input.initial=initial;
    expected.shift_real=real(shifted(:));expected.shift_imag=imag(shifted(:));
    expected.rotated_real=real(rotated(:));expected.rotated_imag=imag(rotated(:));
    expected.noise_real=real(noise(:));expected.noise_imag=imag(noise(:));
    expected.received_real=real(received(:));expected.received_imag=imag(received(:));expected.command_samples=samples;
    cases(end+1)=struct('input',input,'expected',expected); %#ok<AGROW>
end
result.matlab_version=version;result.toolbox=ver('5g');result.generated_at=char(datetime('now','TimeZone','UTC','Format','yyyy-MM-dd''T''HH:mm:ssXXX'));
result.spec_baseline='TA:TS38.213 V15.3.0 section4.2; CFO/AWGN:project models';result.cases=cases;
fid=fopen(outputFile,'w','n','UTF-8');assert(fid>=0);closer=onCleanup(@()fclose(fid));
fprintf(fid,'%s\n',jsonencode(result));fprintf('Exported %d independent channel cases\n',numel(cases));
end
