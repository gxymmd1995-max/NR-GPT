function export_NRSRSReceiver_reference(outputFile)
% 独立MATLAB SRS接收参考。nrSRS/nrSRSIndices/nrResourceGrid生成真实参考信号，
% MATLAB原生LS/SVD/FFT基计算联合FIR、噪声、时延；nrPUSCHCodebook生成标准码本。
% 接收指标算法为项目定义，不冒充3GPP接收机规定；不执行或导入Python。
if nargin<1
    outputFile=fullfile(fileparts(mfilename('fullpath')),'NRSRSReceiver_reference.json');
end
cases=repmat(struct('input',struct(),'expected',struct()),0,1);
for id=0:23
    rng(7300+id,'twister'); D=8; K=288; L=14; R=4; Nfft=512;
    cellCfg=struct('n_size_grid',24,'n_start_grid',10,'bwp_start',10,'bwp_size',24, ...
        'n_rx_antennas',R,'subcarrier_spacing_khz',30,'cyclic_prefix','normal');
    carrier=nrCarrierConfig('NSizeGrid',24,'NStartGrid',10,'SubcarrierSpacing',30);
    if id>=20
        cellCfg.subcarrier_spacing_khz=60;cellCfg.cyclic_prefix='extended';
        carrier.SubcarrierSpacing=60;carrier.CyclicPrefix='extended';L=12;
    end
    ports=[1 2 4]; P=ports(mod(floor(id/2),3)+1); users=1;
    if id>=12 && id<20, users=2; P=2; end
    configs=repmat(struct('uid','','n_ports',P,'n_symbols',4,'start_position',3, ...
        'c_srs',6,'k_tc',2,'cyclic_shift',0,'sequence_id',17,'comb_offset',0,'beta',1),users,1);
    refs=cell(1,users); truth=cell(1,users); rx=complex(zeros(K,L,R)); observed=false(K,L);
    k=(0:K-1).'; phase=exp(-2j*pi*k*(0:D-1)/Nfft);
    for u=1:users
        x=configs(u);x.uid=sprintf('UE%d',u-1);
        if mod(id,2)==1,x.k_tc=4;end
        if users==2,x.k_tc=2;x.cyclic_shift=2*(u-1);end
        if mod(id,4)==3,x.cyclic_shift=(2*x.k_tc+4)/2;end
        if users==2 && mod(id,4)==3,x.cyclic_shift=2*(u-1);x.sequence_id=17+76*(u-1);end
        x.beta=1-.3*(u-1);configs(u)=x;
        s=nrSRSConfig('CSRS',x.c_srs,'NumSRSPorts',P,'NumSRSSymbols',4, ...
            'SymbolStart',L-4,'KTC',x.k_tc,'CyclicShift',x.cyclic_shift,'NSRSID',x.sequence_id);
        s.SRSPositioning=false;s.FrequencyScalingFactor=1;s.CyclicShiftHopping=false;s.CombOffsetHopping=false;
        values=nrSRS(carrier,s)*x.beta/sqrt(P);indices=nrSRSIndices(carrier,s);
        ref=nrResourceGrid(carrier,P);ref(indices)=values;refs{u}=ref;
        observed=observed|any(ref~=0,3);
        taps=complex(zeros(D,P,R));delay=mod(id+u,7);
        gains=(randn(R,P)+1j*randn(R,P))/sqrt(2);
        if mod(id,4)==0,gains(:)=0;gains(1:min(R,P),:)=eye(min(R,P),P);end
        taps(delay+1,:,:)=reshape(gains.',1,P,R);
        if mod(id,3)==2,taps(mod(delay+2,D)+1,:,:)=.15*reshape(gains.',1,P,R);end
        truth{u}=taps;
        for r=1:R
            for p=1:P
                h=phase*taps(:,p,r);
                rx(:,:,r)=rx(:,:,r)+ref(:,:,p).*h;
            end
        end
    end
    variance=.001*ones(K,1);
    if mod(id,3)==0,variance(:)=0;end
    if mod(id,3)==2,variance(145:192)=.03;end
    noise=(randn(K,L,R)+1j*randn(K,L,R)).*sqrt(variance/2);
    rx=rx+noise; locations=find(observed);
    [frequencies,~]=ind2sub([K L],locations);basis=exp(-2j*pi*(frequencies-1)*(0:D-1)/Nfft);
    A=complex(zeros(numel(locations),P*D*users));
    for u=1:users
        ref=refs{u};
        for p=1:P
            v=ref(:,:,p);columns=(u-1)*P*D+(p-1)*D+(1:D);
            A(:,columns)=v(locations).*basis;
        end
    end
    Y=reshape(rx,K*L,R);Y=Y(locations,:);
    C=A\Y; E=Y-A*C;inverse=pinv(A);[U,S,~]=svd(A,'econ');lev=sum(abs(U).^2,2);
    explicit=mod(id,5)~=4;
    if explicit
        mask=~observed; power=abs(reshape(rx,K*L,R)).^2; power=power(mask(:),:);
        [ks,~]=find(mask);dof=ones(size(ks));method='muted_re';
    else
        mask=[];power=abs(E).^2;ks=frequencies;dof=max(1-lev,0);method='ls_residual';
    end
    wide=sum(power,1)/sum(dof);narrow=nan(24,R);counts=zeros(24,1);
    for rb=0:23
        chosen=floor((ks-1)/12)==rb;counts(rb+1)=nnz(chosen);
        if sum(dof(chosen))>1e-8,narrow(rb+1,:)=sum(power(chosen,:),1)/sum(dof(chosen));end
    end
    outUsers=repmat(struct(),0,1);
    for u=1:users
        span=(u-1)*P*D+(1:P*D);cir=reshape(C(span,:),D,P,R);
        h=complex(zeros(K,P,R));for r=1:R,for p=1:P,h(:,p,r)=phase*cir(:,p,r);end,end
        own=any(refs{u}~=0,3);own=own(locations);
        prediction=A(own,span)*C(span,:);gain=mean(sum(abs(A(own,span)*inverse(span,:)).^2,2));
        signal=max(mean(abs(prediction).^2,'all')-mean(wide)*gain,0);
        ownGrid=any(refs{u}~=0,3);symbolPower=[];
        for l=find(any(ownGrid,1))
            bins=find(ownGrid(:,l));symbolPower(end+1,:)=reshape(sum(abs(rx(bins(1):bins(end),l,:)).^2,1),1,R); %#ok<AGROW>
        end
        rssiPerRx=mean(symbolPower,1);rsrpPerRx=max(mean(abs(prediction).^2,1)-wide*gain,0);
        signal=mean(rsrpPerRx);
        item.rssi=mean(rssiPerRx);item.rssi_db=10*log10(item.rssi);
        item.rsrp=signal;item.rsrp_db=10*log10(signal);item.rssi_per_rx=rssiPerRx;item.rsrp_per_rx=rsrpPerRx;
        coefficientNoise=mean(wide)*reshape(sum(abs(inverse(span,:)).^2,2),D,P);
        delayPower=max(sum(abs(cir).^2,[2 3])-R*sum(coefficientNoise,2),0);
        [~,peak]=max(delayPower);meanDelay=sum(delayPower.*(0:D-1).')/sum(delayPower);
        first=find(delayPower>=max(delayPower)*.1,1)-1;
        sounded=any(any(refs{u}~=0,3),2);
        [ri,tpmi,score]=chooseCodebook(h(sounded,:,:),mean(wide));
        item.uid=configs(u).uid;item.cir_real=real(cir(:));item.cir_imag=imag(cir(:));
        item.channel_real=real(h(:));item.channel_imag=imag(h(:));item.delay_power=delayPower;
        item.delay_samples=peak-1;item.mean_delay_samples=meanDelay;item.signal_power=signal;
        item.first_path_delay_samples=first;
        item.snr_db=10*log10(signal/max(mean(wide),1e-12));item.ri=ri;item.tpmi=tpmi;item.score=score;
        if u==1,outUsers=item;else,outUsers(end+1)=item;end %#ok<AGROW>
    end
    input.cell=cellCfg;input.resources=configs;input.n_delay_taps=D;
    input.rx_real=real(rx(:));input.rx_imag=imag(rx(:));input.explicit_noise_mask=explicit;
    input.noise_mask=mask(:);input.generated_noise_variance=variance;
    expected.noise_method=method;expected.wide_per_rx=wide;expected.narrow_per_rx=narrow(:);
    expected.counts=counts;expected.users=outUsers;expected.condition_number=S(1,1)/S(end,end);
    expected.residual_power=mean(abs(E).^2,'all');
    cases(end+1)=struct('input',input,'expected',expected); %#ok<AGROW>
end
result.matlab_version=version;result.toolbox=ver('5g');
result.generated_at=char(datetime('now','TimeZone','UTC','Format','yyyy-MM-dd''T''HH:mm:ssXXX'));
result.spec_baseline='TS 38.211 V15.2.0 SRS and PUSCH codebook; receiver algorithms project-defined';
result.note='Actual nrSRS/nrSRSIndices/nrResourceGrid; independent native MATLAB LS/noise/delay and nrPUSCHCodebook selection; frequency-domain input';
result.cases=cases;
fid=fopen(outputFile,'w','n','UTF-8');assert(fid>=0);closer=onCleanup(@()fclose(fid));
fprintf(fid,'%s\n',jsonencode(result));fprintf('Exported %d independent SRS receiver cases\n',numel(cases));
end

function [bestRank,bestTPMI,bestScore]=chooseCodebook(H,noise)
% H[K,P,R]；每个候选按单位Frobenius范数比较等总发送功率的平均互信息。
P=size(H,2);R=size(H,3);counts=[1 0 0 0;6 3 0 0;0 0 0 0;28 22 7 5];
bestScore=-inf;bestRank=1;bestTPMI=0;
for rank=1:min(P,R)
    for tpmi=0:counts(P,rank)-1
        w=nrPUSCHCodebook(rank,P,tpmi,false).';w=w/norm(w,'fro');scores=zeros(size(H,1),1);
        for k=1:size(H,1)
            h=reshape(H(k,:,:),P,R).';g=h*w;
            eigenvalues=max(real(eig(g'*g)),0);
            scores(k)=sum(log2(1+eigenvalues/max(noise,1e-12)));
        end
        score=mean(scores);
        if score>bestScore+1e-10,bestScore=score;bestRank=rank;bestTPMI=tpmi;end
    end
end
end
