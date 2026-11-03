function export_NRPUCCH0_multiuser_reference(outputFile)
% 三用户CDM同RB资源；真实5G Toolbox序列/OFDM，原生MATLAB独立叠加信道及分用户相关。
% 固定R15 38.211 V15.2.0 6.3.2.2/3；保持14*slot寻址，真实CP用于OFDM。
if nargin<1,outputFile=fullfile(fileparts(mfilename('fullpath')),'NRPUCCH0_multiuser_reference.json');end
cases=struct('input',{},'expected',{});
activity=[1 1 1;1 1 0;1 0 1;0 1 1;1 0 0;0 1 0];
gains=[1 .3+.5j -.4j;.3j .7 .6+.5j];threshold=.15;fc=3500000123;
for id=0:11
    cp='normal';scs=30;if mod(id,2)==1,cp='extended';scs=60;end
    cellCfg=struct('n_cell_id',17,'n_size_grid',6,'n_start_grid',10,'bwp_start',11,...
        'bwp_size',4,'n_rx_antennas',2,'n_slot',3,'cyclic_prefix',cp,'subcarrier_spacing_khz',scs);
    carrier=nrCarrierConfig('NCellID',17,'NSizeGrid',6,'NStartGrid',10,'NSlot',3,...
        'CyclicPrefix',cp,'SubcarrierSpacing',scs);
    active=logical(activity(floor(id/2)+1,:));shifts=mod([0 2 4]+floor(id/6),12);acks=mod(id+(0:2),2);
    configs=cell(1,3);mixed=[];
    for u=1:3
        configs{u}=nrPUCCH0Config('NSizeBWP',4,'NStartBWP',11,'PRBSet',0,'SymbolAllocation',[8 2],...
            'InitialCyclicShift',shifts(u),'HoppingID',731,'GroupHopping','enable',...
            'FrequencyHopping','intraSlot','SecondHopStartPRB',3,'Interlacing',false);
        seq=nrPUCCH0(acks(u),[],[8 2],'normal',3,731,'enable',shifts(u),'enabled');
        grid=nrResourceGrid(carrier,1);grid(nrPUCCHIndices(carrier,configs{u}))=seq;
        tx=nrOFDMModulate(carrier,grid,'Nfft',128,'CarrierFrequency',fc,'Windowing',0);
        advanced=[tx(3:end,:);zeros(2,1)];spatial=advanced*gains(:,u).';
        if ~active(u),spatial(:)=0;end
        path=[zeros(5,2);spatial(1:end-5,:)];fs=128*scs*1000;t=(0:size(tx,1)-1).';
        offset=path.*exp(1j*(.23+2*pi*731*t/fs));
        if isempty(mixed),mixed=zeros(size(offset));end
        mixed=mixed+offset;
    end
    rng(12000+id,'twister');standard=(randn(size(mixed))+1j*randn(size(mixed)))/sqrt(2);
    snrDb=-5+5*mod(id,3);noisePower=mean(abs(mixed).^2,1)*10^(-snrDb/10);
    received=mixed+standard.*sqrt(noisePower);
    corrected=received.*exp(-1j*(.23+2*pi*731*t/fs));corrected=[corrected(4:end,:);zeros(3,2)];
    rxGrid=nrOFDMDemodulate(carrier,corrected,'Nfft',128,'CarrierFrequency',fc,'CyclicPrefixFraction',.5);
    users=struct([]);
    for u=1:3
        idx=nrPUCCHIndices(carrier,configs{u});y=complex(zeros(24,2));
        for r=1:2,plane=rxGrid(:,:,r);y(:,r)=plane(idx);end
        energy=sum(abs(y).^2,'all');metrics=zeros(1,2);correlations=complex(zeros(2,2,2));
        for bit=0:1
            reference=nrPUCCH0(bit,[],[8 2],'normal',3,731,'enable',shifts(u),'enabled');
            proj=reshape(sum(reshape(y,12,2,2).*conj(reshape(reference,12,2)),1),2,2);
            correlations(:,:,bit+1)=proj/12;
            metrics(bit+1)=sum(abs(proj).^2,'all')/(12*energy);
        end
        [metric,best]=max(metrics);
        item=struct('uid',sprintf('UE%d',u-1),'detected',metric>threshold,'best_bit',best-1,...
            'metric',metric,'metrics',metrics,'correlation_real',real(correlations(:)),...
            'correlation_imag',imag(correlations(:)));
        if u==1,users=item;else,users(end+1)=item;end %#ok<AGROW>
    end
    input=struct('cell',cellCfg,'initial_shifts',shifts,'harq_ack',acks,'active',active,...
        'gain_real',real(gains),'gain_imag',imag(gains),'snr_db',snrDb,'detection_threshold',threshold,...
        'carrier_frequency_hz',fc,'seed',12000+id,'standard_real',real(standard(:)),'standard_imag',imag(standard(:)));
    expected=struct('n_samples',size(mixed,1),'mixed_real',real(mixed(:)),'mixed_imag',imag(mixed(:)),...
        'received_real',real(received(:)),'received_imag',imag(received(:)),'users',users);
    cases(end+1)=struct('input',input,'expected',expected); %#ok<AGROW>
end
result=struct('matlab_version',version,'toolbox',ver('5g'),...
    'generated_at',char(datetime('now','TimeZone','UTC','Format','yyyy-MM-dd''T''HH:mm:ssXXX')),...
    'spec_baseline','TS38.211 V15.2.0; TS38.213 V15.3.0; fixed14 sequence addressing, actual CP OFDM',...
    'scope','Three orthogonal cyclic-shift groups, common known synchronization, independent flat complex gains; native MATLAB receiver metric',...
    'cases',cases);
fid=fopen(outputFile,'w','n','UTF-8');assert(fid>=0);closer=onCleanup(@()fclose(fid));fprintf(fid,'%s\n',jsonencode(result));
fprintf('Exported %d actual MATLAB multiuser waveform/receiver cases\n',numel(cases));
end
