function export_NRPUCCH0_reference(outputFile)
% 固定R15子集：38.211 V15.2.0 6.3.2.2/3；38.213 V15.3.0表9.2.3-3/-4,9.2.5-1/-2。
% 只调用公开5G Toolbox产生序列/RE/波形；原生MATLAB独立建立候选相关接收机。
if nargin<1,outputFile=fullfile(fileparts(mfilename('fullpath')),'NRPUCCH0_reference.json');end
payloads={};
for n=1:2
    for value=0:2^n-1
        ack=bitget(value,n:-1:1).';
        for sr=[-1 0 1],payloads{end+1}={ack,sr};end %#ok<AGROW>
    end
end
payloads{end+1}={[],0};payloads{end+1}={[],1};
groups={'neither','enable'};cases=struct('input',{},'expected',{});waves=struct('input',{},'expected',{});id=0;
for ns=1:2
 for gh=1:2
  for cs=0:11
   for ui=1:numel(payloads)
    cp='normal';scs=30;if mod(id,5)==0,cp='extended';scs=60;end
    cellCfg=struct('n_cell_id',17,'n_size_grid',6,'n_start_grid',10,'bwp_start',11,'bwp_size',4,...
        'subcarrier_spacing_khz',scs,'cyclic_prefix',cp,'n_slot',mod(id,10*(scs/15)),'n_rx_antennas',2);
    carrier=nrCarrierConfig('NCellID',17,'NSizeGrid',6,'NStartGrid',10,...
        'SubcarrierSpacing',scs,'CyclicPrefix',cp,'NSlot',cellCfg.n_slot);
    L=14;if strcmp(cp,'extended'),L=12;end
    hopping=ns==2 && mod(id,2)==0;hop='neither';second=-1;
    if hopping,hop='intraSlot';second=3;end
    nid=mod(id*79,1024);start=L-ns-1;
    pucch=nrPUCCH0Config('NSizeBWP',4,'NStartBWP',11,'PRBSet',0,'SymbolAllocation',[start ns],...
        'InitialCyclicShift',cs,'HoppingID',nid,'GroupHopping',groups{gh},'FrequencyHopping',hop,'Interlacing',false);
    if hopping,pucch.SecondHopStartPRB=second;end
    ack=payloads{ui}{1};sr=payloads{ui}{2};srBits=[];if sr>=0,srBits=sr;end
    rawSymbols=nrPUCCH(carrier,pucch,{ack,srBits});
    % R15原文6.3.2.2.2固定14*slot；当前Toolbox extended CP使用12*slot。
    % 仅序列生成显式使用normal CP参数保证Gold寻址14；物理映射/OFDM仍用真实CP。
    hoppingFlag='disabled';if hopping,hoppingFlag='enabled';end
    symbols=nrPUCCH0(ack,srBits,[start ns],'normal',cellCfg.n_slot,nid,groups{gh},cs,hoppingFlag);
    idx=nrPUCCHIndices(carrier,pucch,'IndexStyle','subscript','IndexBase','0based');
    input=struct('cell',cellCfg,'prb',0,'start_symbol',start,'n_symbols',ns,...
        'initial_cyclic_shift',cs,'hopping_id',nid,'group_hopping',groups{gh},...
        'second_hop_prb',second,'harq_ack',reshape(ack,1,[]),'sr',sr);
    expected=struct('real',real(symbols(:)),'imag',imag(symbols(:)),...
        'indices',double([idx(:,3) idx(:,2) idx(:,1)]),...
        'toolbox_default_real',real(rawSymbols(:)),'toolbox_default_imag',imag(rawSymbols(:)));
    cases(end+1)=struct('input',input,'expected',expected); %#ok<AGROW>
    % 每种CP/跳频/组跳变的代表性时域链路，包含所有UCI类别及DTX。
    if cs==0 && gh==1
        beta=.7;fc=3500000123;nfft=128;snrDb=12;freq=731;phase=.23;delay=3;
        grid=nrResourceGrid(carrier,1);lin=nrPUCCHIndices(carrier,pucch);
        if ~isempty(symbols),grid(lin)=beta*symbols;end
        tx=nrOFDMModulate(carrier,grid,'Nfft',nfft,'CarrierFrequency',fc,'Windowing',0);
        gain=[1 .6j];clean=tx*gain;delayed=[zeros(delay,2);clean(1:end-delay,:)];
        fs=nfft*scs*1000;t=(0:size(tx,1)-1).';
        offset=delayed.*exp(1j*(phase+2*pi*freq*t/fs));
        rng(9000+id,'twister');standard=(randn(size(offset))+1j*randn(size(offset)))/sqrt(2);
        noisePower=mean(abs(offset).^2,1)*10^(-snrDb/10);
        received=offset+standard.*sqrt(noisePower);
        corrected=received.*exp(-1j*(phase+2*pi*freq*t/fs));
        corrected=[corrected(delay+1:end,:);zeros(delay,2)];
        rxGrid=nrOFDMDemodulate(carrier,corrected,'Nfft',nfft,'CarrierFrequency',fc,'CyclicPrefixFraction',1);
        extracted=complex(zeros(12*ns,2));
        for r=1:2,plane=rxGrid(:,:,r);extracted(:,r)=plane(lin);end
        nAck=numel(ack);srEnabled=sr>=0;
        correlations=complex(zeros(ns,2,0));
        candidates=struct('harq_ack',{},'sr',{},'metric',{});ener=sum(abs(extracted).^2,'all');
        for val=0:2^nAck-1
            bits=bitget(val,nAck:-1:1).';possibleSR=-1;
            if nAck==0,possibleSR=1;elseif srEnabled,possibleSR=[0 1];end
            for ss=possibleSR
                srCandidate=[];if ss>=0,srCandidate=ss;end
                ref=nrPUCCH0(bits,srCandidate,[start ns],'normal',cellCfg.n_slot,nid,groups{gh},cs,hoppingFlag);
                y=reshape(extracted,12,ns,2);ref=reshape(ref,12,ns);
                proj=sum(y.*conj(ref),1);metric=0;
                if ener>0,metric=min(1,max(0,sum(abs(proj).^2,'all')/(12*ener)));end
                item=struct('harq_ack',reshape(bits,1,[]),'sr',ss,'metric',metric);
                candidates(end+1)=item; %#ok<AGROW>
                correlations(:,:,numel(candidates))=reshape(proj/12,ns,2);
            end
        end
        [metric,best]=max([candidates.metric]);threshold=.49;if ns==2,threshold=.42;end
        decision=struct('detected',ener>0 && metric>threshold,'best',candidates(best),'metric',metric,...
            'candidates',candidates,'resource_power',ener/numel(extracted));
        decision.correlation_real=real(correlations(:));decision.correlation_imag=imag(correlations(:));
        decodeCarrier=carrier;decodeCarrier.CyclicPrefix='normal';
        [toolboxBits,~,toolboxMetric]=nrPUCCHDecode(decodeCarrier,pucch,[nAck srEnabled],extracted);
        winput=struct('resource',input,'beta',beta,'carrier_frequency_hz',fc,'snr_db',snrDb,...
            'frequency_offset_hz',freq,'initial_phase_rad',phase,'delay_samples',delay,...
            'standard_real',real(standard(:)),'standard_imag',imag(standard(:)));
        wexpected=struct('n_samples',size(tx,1),'tx_real',real(tx(:)),'tx_imag',imag(tx(:)),...
            'rx_real',real(received(:)),'rx_imag',imag(received(:)),...
            'decision',decision,'toolbox_bits',{toolboxBits},'toolbox_metric',toolboxMetric);
        waves(end+1)=struct('input',winput,'expected',wexpected); %#ok<AGROW>
    end
    id=id+1;
   end
  end
 end
end
result=struct('matlab_version',version,'toolbox',ver('5g'),...
    'generated_at',char(datetime('now','TimeZone','UTC','Format','yyyy-MM-dd''T''HH:mm:ssXXX')),...
    'spec_baseline','TS38.211 V15.2.0; TS38.213 V15.3.0; one RB, no interlacing, no later-release features',...
    'sequence_adapter','R15 6.3.2.2.2 uses fixed14*slot. nrPUCCH0 CP=normal for sequence only, actual carrier CP for OFDM/indices; default Toolbox symbols also retained.',...
    'sequence_cases',cases,'waveform_cases',waves);
fid=fopen(outputFile,'w','n','UTF-8');assert(fid>=0);closer=onCleanup(@()fclose(fid));
fprintf(fid,'%s\n',jsonencode(result));
fprintf('Exported %d Toolbox sequence/RE and %d independent waveform/receiver cases\n',numel(cases),numel(waves));
end
