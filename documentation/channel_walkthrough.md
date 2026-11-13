# 物理信道新手阅读指南：坐标、长度与链路

按顺序读各信道并动手练习，见 [NR Release 15 物理层学习路线](learning_path.md)。

各信道教程入口：[PUCCH F0](../src/pucch/NRPUCCH0.md)、[F1](../src/pucch/NRPUCCH1.md)、[F2](../src/pucch/NRPUCCH2.md)、[F3](../src/pucch/NRPUCCH3.md)、[F4](../src/pucch/NRPUCCH4.md)、[PUSCH](../src/pusch/NRPUSCH.md)、[PDSCH](../src/pdsch/NRPDSCH.md)、[PDCCH](../src/pdcch/NRPDCCH.md)、[SRS](../src/srs/NRSRS.md)、[SSB](../src/ssb/NRSSB.md)、[PRACH](../src/prach/NRPRACH.md)。各类文档的“新手导读”串起信号生成、资源位置、配置差异和接收算法；原有字段表保留为API参考。

## 一格RE是什么

资源网格横轴为OFDM符号，纵轴为子载波。一个RE是“某个符号上的某个子载波”，装一个复数。一个RB沿频率方向有12个子载波；RB数不是用户比特数，也不是时域采样点数。

```text
子载波 ↑      符号0  符号1  符号2  符号3 → 时间
    k+2         D      D      R      D
    k+1         D      D      R      D    D=数据，R=参考信号
    k           D      D      R      D    示意图，不表示所有信道使用此DMRS布局
```

普通CP每slot有14个符号，扩展CP有12个。各信道还有自己的CP支持限制；例如SSB当前只接受普通CP。频域资源只占部分符号时，发射机仍可能返回完整slot波形，未映射位置为零。频域的零RE经过IFFT后不对应时域上逐点的零；只有整个符号未占用时才有对应的静默符号段。

## 统一坐标与单位

以下READ-1/2为本文自编号，是根据TS38.211 V15.2.0 §4.4、§5.3.1及平台采样率约定的推导，不是原文公式号。PRACH有独立FFT/CP，另读PRACH教程。

$$
 k_0=12(N_{BWP}^{start}-N_{grid}^{start}+p),\qquad
 f_k=(k-6N_{grid}^{size})\Delta f,\qquad B_{RB}=12\Delta f.\tag{READ-1}
$$

| 变量 | 意义、范围、单位、维度 |
|---|---|
| N_BWP_start | BWP起始CRB；把BWP局部位置换到公共频率坐标；取值范围/约束：非负整数且BWP整体位于载波内；单位：CRB索引；维度/类型：整数标量 |
| N_grid_start | 载波网格起始CRB；转换到载波局部坐标时减去它；取值范围/约束：NRCell范围0..2199，且满足BWP包含约束；单位：CRB索引；维度/类型：整数标量 |
| p | BWP局部首RB号，用于换算首子载波；范围：整数0..BWP_size−1且资源装入BWP；单位：RB索引；维度：整数标量 |
| k0 | 载波局部首子载波号，定位分配起点；范围：12×(BWP_start−grid_start+p)，在载波网格内；单位：子载波索引；维度：整数标量 |
| N_grid_size | 载波资源块数量；确定网格频宽与中心；取值范围/约束：当前平台整数1..275；单位：RB；维度/类型：整数标量 |
| k | 载波局部子载波号，用于换算基带频率；范围：整数0..12N_grid_size−1；单位：子载波索引；维度：整数标量 |
| Delta_f | 子载波间隔，决定频率点距离和有效符号长度；范围：正实数，15×2^mu kHz，代公式时用Hz；单位：Hz；维度：实标量 |
| f_k | 第k个子载波相对网格中心的频率；范围：由(k−6N_grid_size)×Delta_f计算，可为负；单位：Hz；维度：实标量 |
| B_RB | 一个RB的频域宽度，用于带宽计算；范围：12×Delta_f>0；单位：Hz；维度：实标量 |

例如UL30 kHz、52 RB、BWP与载波同起点、p=4：首子载波k0=48，频率−7.92 MHz；一个RB宽360 kHz。SSB使用载波局部start_subcarrier，SRS的frequency_shift也是载波局部RB，不能都套成BWP局部p。

$$
 s_l=\sum_{i=0}^{l-1}(N_{FFT}+C_i),\qquad
 t_l=s_l/F_s,\qquad t_l^{useful}=(s_l+C_l)/F_s,\qquad
 T_{alloc}=\frac{\sum_{l=l_0}^{l_0+S-1}(N_{FFT}+C_l)}{F_s}.\tag{READ-2}
$$

| 变量 | 意义、范围、单位、维度 |
|---|---|
| l | 当前slot局部符号号，用于计算该符号起点；范围：0..symbols_per_slot−1；单位：符号索引；维度：整数标量 |
| l0 | 分配首个slot符号号，用于连续时间求和起点；范围：整数0..symbols_per_slot−S；单位：符号索引；维度：整数标量 |
| S | 连续分配符号数量，用于时间求和长度；范围：正整数，l0+S≤symbols_per_slot；还受信道格式约束；单位：符号数；维度：整数标量 |
| N_FFT | 小区FFT长度，确定每有效符号采样数；范围：正整数，按NRCell平台FFT规则；单位：采样点；维度：整数标量 |
| C_i | slot第i符号的CP长度，用于时间拼接；范围：正整数，来自slot_cp_lengths_samples；单位：采样点；维度：每符号整数 |
| s_l | 第l符号CP首点的slot局部采样索引；范围：sum_i<l(N_FFT+C_i)，l=0时为0；单位：采样点索引；维度：整数标量 |
| Fs | 小区采样率；在样点和秒之间换算；取值范围/约束：Fs=cell.n_fft×cell子载波间隔Hz，正数；单位：Hz，即sample/s；维度/类型：实标量 |
| t_l | 第l符号CP首点的slot局部时间；范围：s_l/Fs≥0；单位：s；维度：实标量 |
| t_l_useful | 第l符号有效段起始时间，用于FFT窗口定位；范围：(s_l+C_l)/Fs>t_l；单位：s；维度：实标量 |
| T_alloc | 连续分配的总时间，含各符号CP；范围：sum_l=l0..l0+S−1(N_FFT+C_l)/Fs>0；单位：s；维度：实标量 |

一个有效符号为Nfft点，CP额外增加C_i点。CP可能随符号/slot变化，不能把平均slot时长除以14后当成每个符号的精确长度。当前slot的精确长度从NRCell.slot_cp_lengths_samples读取。

```python
from cell import NRCell
cell = NRCell(n_size_grid=52, subcarrier_spacing_khz=30)
starts = [0]
for cp in cell.slot_cp_lengths_samples:
    starts.append(starts[-1] + cell.n_fft + cp)
for l in [0, 2, 12, 13]:
    print(l, 'CP起点/终点样点=', starts[l], starts[l+1],
          '起点us=', starts[l] / cell.sample_rate_hz * 1e6)
assert starts[-1] == cell.samples_per_slot
```

## 从比特到接收结果

```mermaid
flowchart LR
    A[业务比特或已知参考序列] --> B[信道专用编码及序列处理]
    B --> C[数据与参考映射到NRGrid]
    C --> D[NROFDM：相位处理 IFFT 加CP]
    D --> E[NRChannel：复增益 样点延迟 CFO SNR噪声]
    E --> F[已知同步量补偿 去CP FFT]
    F --> G[提取资源 信道估计 均衡或相关]
    G --> H[比特译码或信道测量]
```

逻辑层/端口、物理发送天线、接收天线是三个概念。多层发射数组要通过明确的信道矩阵变成接收分支；cell.n_tx_antennas不会自动生成预编码。普通OFDM信道收发类输入输出完整slot，SRSReceiver直接输入已解调频域网格；PRACH独立处理时序。

已知CFO、时延补偿参数是仿真调用者提供的同步信息，不代表接收机自动估计了它们。CRC通过、检测门限通过、LDPC收敛也不是同一判断。幅度/功率未做射频标定时不应解释成dBm。

## CSI-RS 和 PT-RS 分别测什么

| 参考信号 | 如何选位置 | 接收端如何使用 | 运行示例 |
|---|---|---|---|
| CSI-RS | 先选slot符号和CRB区间；Row1每RB放3个点，Row2每RB放1个点，半密度时只选偶数或奇数CRB | 用已知序列估计每个接收分支的平坦复增益，同时报告参考点的平均接收功率 | [100 MHz CSI-RS](../examples/csirs/NRCSIRS_100MHz_30kHz_demo.py) |
| 上行PT-RS | 以PUSCH分配为范围，从关联DMRS序列取参考；按时域密度选符号、按频域密度选RB | 用已知信道合并参考点，测量每个参考符号的公共相位；可在参考之间插值后反旋数据点 | [100 MHz上行PT-RS](../examples/ptrs/NRUplinkPTRS_100MHz_30kHz_demo.py) |
| 下行PT-RS | 以PDSCH分配为范围，同样按密度选符号及RB，采用下行规范的偏移表 | 同样测量并补偿公共相位 | [100 MHz下行PT-RS](../examples/ptrs/NRDownlinkPTRS_100MHz_30kHz_demo.py) |

例如两个参考分别落在符号1和6，其相位由3.00 rad变到3.90 rad。直接测到的第二个相角约为−2.38 rad，因为相角会在±π折返；先解缠再插值，才能正确补偿中间符号。独立示例用一个普通数据 RE 演示这个过程。完整业务链示例可比较同一段接收波形在开启和关闭补偿时的星座与 CRC。[共享信道 PT-RS 对照](../examples/common/NRSharedChannel_PTRS_demo.py)

## 看图的顺序

先看grid确认时频占用，再看IFFT/CP后的波形，最后看相关分数或均衡星座和CRC。发射QAM星座、信道后的接收星座、均衡星座是不同阶段；循环移位产生的是序列逐点相位斜坡，不能把相关复增益图当作12个循环移位的单位圆。

示例的NRPlotConfig控制显示阶段，图片只显示、不保存。各examples模块README列出实际脚本。协议与MATLAB验证范围以各模块validation报告为准，示意图和Python链路自测不构成新的MATLAB实测证据。

各信道文档现含Python生成的PNG图例；[统一绘图脚本](../examples/common/plot_NRChannel_documentation.py)默认只显示，传`--save`可重新生成各examples模块的文档图片。
