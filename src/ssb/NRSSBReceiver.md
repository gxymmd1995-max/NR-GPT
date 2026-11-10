# NRSSBReceiver：已知时频窗口内的PCI、SSB索引与MIB恢复

[源码](NRSSBReceiver.py)。参考序列及BCH依据TS38.211 V15.2.0 §7.4.2/§7.4.3/§7.4.1.4、TS38.212 V15.2.0 §7.1；相关搜索、LS/MRC及SC译码为项目接收算法。

## 配置与输入

| 字段 | 含义、范围、单位、示例 |
|---|---|
| resource | NRSSB；使用其时频窗口、l_max及cell几何/时序；cell的PCI、ssb_index和half_frame可为错误初值，不作为真实接收标签 |
| carrier_frequency_hz=0 | 有限非负载频Hz，例3.5e9；与发送一致的NR符号相位补偿 |
| detection_threshold=.1 | 有限0..1的PSS/SSS相关能量门限，严格大于；工程门限而非CFAR |
| plot_config=None | NRPlotConfig或None；None关闭；例NRPlotConfig(enabled=True,channel='SSB') |

构造/__post_init__验证上述字段。receive(waveform,*,known_delay_samples=0,known_frequency_offset_hz=0,known_initial_phase_rad=0,plotter=None)：有限complex[Rx,T]完整slot，Rx=cell.n_rx_antennas、T=cell.samples_per_slot。已知净时延为整数采样点，CFO为Hz，初相rad；先反旋/提前补偿后NROFDM解调。plotter是可选共享NRStagePlotter。这里的同步补偿量是输入，**没有实现未知时间位置或未知频偏的盲捕获**。

在给定240×4窗口：三条PSS非相干天线相关确定NID2，再遍历336条对应SSS确定NID1，得到PCI；不读取resource.cell.n_cell_id作为真值。随后按恢复PCI构造DMRS，搜索8个i_bar：Lmax4同时搜索索引0..3和半帧0/1，Lmax8/64搜索索引低3位；Lmax64的高3位由CRC通过的BCH载荷恢复。

## 算法与变量

文档自编号SSB-RX-1/2；序列来自上述固定规范，接收公式为项目算法：

$$
\eta(q)=\frac{\sum_r|\sum_{n=0}^{126}Y_r[n]d_q[n]^*|^2}{127\sum_{r,n}|Y_r[n]|^2},\quad
\widehat q=\arg\max_q\eta(q).\tag{SSB-RX-1}
$$

Y为complex[Rx,127]已提取PSS或SSS，d_q为对应候选int8[127]；q对PSS为0..2，对SSS为0..335。eta为float[3]/float[336]，clip至0..1，零能量取0；Rx为天线数，r/n为零基索引。两个最大分数均超过门限才detected=True，无绝对功率单位。

$$
\widehat H_{r,l}=\operatorname{mean}_{m\in\mathcal D_l}Y_r[m]R_l[m]^*,\quad
z_k=\sum_r\widehat H_{r,l(k)}^*Y_r[k],\quad
w_k=\sum_r|\widehat H_{r,l(k)}|^2,\quad\widehat x_k=z_k/w_k.\tag{SSB-RX-2}
$$

l对应PBCH所在3个符号；D_l为60/24/60个DMRS索引，R为complex单位模参考；H为complex[Rx,3]的每符号平坦复增益。k遍历432个PBCH数据RE；z/x为complex[432]，w为非负float[432]，零权重时x取0。软值按z的实/虚部展开成float[864]，正值支持0，解物理加扰后送BCH SC。未标定绝对噪声，不是频选/多径插值均衡。

DMRS索引搜索使用每候选完整144点与参考的相关模平方、跨Rx求和；先假设块内近似恒定选索引，再按符号LS/MRC。相同低3位的64候选无法仅靠DMRS区分，完整索引由BCH extra_bits的3个MSB与低3位拼接。

## 输出

| 字段 | 含义、范围、单位与维度 |
|---|---|
| detected | PSS与SSS均过门限，bool；不等于CRC成功 |
| cell_id | 搜索到PCI0..1007，未检测为None |
| ssb_index | 搜索索引；Lmax64在CRC通过时为完整0..63，CRC失败时仅为低3位诊断值；未检测None |
| mib | 24位list；未检测None，CRC失败仍有候选 |
| sfn_lsb | 从BCH恢复的SFN低4位，拼接完整帧号；范围：整数0..15；未检测None；单位：帧号低位；维度：整数标量/None |
| system_frame_number | 从MIB高6位与低4位恢复的完整SFN；范围：整数0..1023；未检测None，CRC失败仅诊断；单位：帧索引；维度：整数标量/None |
| half_frame | 恢复的半帧标识，用于确定前/后半帧；范围：0/1；未检测None；单位：半帧标识；维度：整数标量/None |
| extra_bits | BCH附加3位，按Lmax解释索引高位或kSSB字段；范围：每点0/1；未检测None，须CRC通过才有效；单位：bit；维度：list[3]/None |
| crc_ok | BCH CRC bool；未检测False，不能只凭detected接受广播 |
| pss_metrics | 3个NID2候选的PSS相关分数，用于选择组内ID；范围：每点0..1，零能量时0；单位：无量纲；维度：float[3] |
| sss_metrics | 336个NID1候选的SSS相关分数，用于选择ID组；范围：每点0..1，零能量时0；单位：无量纲；维度：float[336] |
| channel_estimates | complex[Rx,3]，含发送beta，三个PBCH符号的平坦估计 |
| equalized_symbols | complex[432]按规范PBCH映射顺序 |
| rx_grid | complex[Rx,slot符号数,载波子载波数] |

绘图rx.pss_metrics、rx.sss_metrics、rx.dmrs_metrics及rx.pbch和OFDM步骤，只显示不保存。零信号不解码；不将CRC失败候选的SFN/索引当作有效广播。

```python
from dataclasses import replace
from cell import NRCell
from ssb import NRSSB,NRSSBTransmitter,NRSSBReceiver
r=NRSSB(NRCell(n_cell_id=1007,n_size_grid=24),ssb_index=7)
sent=NRSSBTransmitter(r).transmit([0,1]*12,sfn_lsb=6)
unknown=replace(r,cell=replace(r.cell,n_cell_id=0),ssb_index=0)
out=NRSSBReceiver(unknown).receive(sent['waveform'])
assert out['cell_id']==1007 and out['ssb_index']==7 and out['crc_ok']
```

边界：已知时频窗口、同numerology、平坦块/符号信道、足够小的剩余同步误差；没有盲时域滑动PSS捕获、盲CFO搜索、Case A～E扫描、SCL、跨SSB软合并、频选多径插值或真实MIB语义/CORESET0解读。参见[验证报告](../../documentation/validation/NRSSB_validation.md)。

## 新手处理流程与资源图入口

已知240×4窗口内，先搜索3个PSS确定NID2，再搜索336个SSS确定NID1，组成PCI；再搜索8个DMRS索引假设。Lmax4联合区分半帧，Lmax64仅靠DMRS得到低3位，高位由BCH恢复。每PBCH符号用DMRS估平坦信道、MRC、解物理扰码与Polar/CRC，再恢复载荷和SFN。检测到PSS/SSS不代表BCH CRC成功；未实现任意录波中的盲时间/CFO捕获或真实MIB语义解析。

[NRSSB的时频位置、长度、配置变化及图例](NRSSB.md)与[统一坐标/采样点换算](../../documentation/channel_walkthrough.md)提供完整阅读顺序。当前类的输入输出单位、形状及异常约束以上文字段/API节为准。

## 逐变量说明

以下变量对应本文已有公式或算法表达式；规范基线和章节沿用对应公式处的引用。每行只定义一个变量，同名符号只在该公式上下文有效。

| 变量 | 含义与用途 | 范围/约束 | 单位 | 维度/类型 |
|---|---|---|---|---|
| q | 同步序列候选号，遍历待检ID | PSS为0..2，SSS为0..335 | 候选索引 | 整数标量 |
| r | Rx分支索引，遍历接收天线 | 0..Rx−1 | 天线索引 | 整数标量 |
| n | 同步序列点索引，执行127点相关 | 0..126 | 序列点索引 | 整数标量 |
| Y | 提取的PSS/SSS观测，供同步相关 | 有限复数 | 归一化复幅度 | complex[Rx,127] |
| d_q | 候选q的本地同步序列 | 每点−1或+1 | 归一化实幅度 | int8[127] |
| eta(q) | 同步候选的能量归一化相关分数 | 0..1，零观测时0 | 无量纲 | 每候选实标量 |
| q_hat | 得分最高的同步候选号，确定ID | PSS为0..2，SSS为0..335 | 候选索引 | 整数标量 |
| H_hat | 每PBCH符号每Rx的平坦增益估计 | 有限复数，含发送beta | 归一化复增益 | complex[Rx,3] |
| l | 三个PBCH符号的局部符号索引 | 块内1/2/3；映射时加start_symbol | 块内符号索引 | 整数标量 |
| D_l | 该符号的DMRS位置集合，决定LS平均样本 | 块内符号1/3各60个、符号2为24个 | RE索引 | 一维整数集合 |
| m | DMRS位置遍历索引，执行参考去相位 | 属于D_l | RE索引 | 整数标量 |
| R_l | 当前符号本地DMRS参考 | 每点单位模复数 | 归一化复幅度 | complex[60]或complex[24] |
| Y_r[m] | RX2中第r支路的参考RE观测 | 有限复数，与RX1的127点Y提取对象不同 | 归一化复幅度 | 复标量 |
| k | PBCH数据点序号，遍历432个QPSK | 0..431 | 数据点索引 | 整数标量 |
| l(k) | 数据点k所属的PBCH符号，选择信道估计 | 块内1/2/3 | 符号索引 | 整数标量 |
| z_k | 跨Rx匹配合并分子，供软值生成 | 有限复数 | 归一化复幅度 | 复标量，整体complex[432] |
| w_k | 跨Rx信道能量和，作为均衡分母 | 实数≥0；为0时输出均衡点0 | 归一化增益平方 | 实标量，整体float[432] |
| x_hat_k | 均衡PBCH QPSK点，供星座诊断 | 有限复数，理想无噪声落QPSK星座 | 归一化复幅度 | 复标量，整体complex[432] |
