# NRPDSCHReceiver：多层DMRS联合估计与ZF均衡

[源码](NRPDSCHReceiver.py)。固定发送依据TS38.211 V15.2.0 §7.3.1/§7.4.1.1及表7.3.1.3-1、7.4.1.1.2-1～5，编码依据TS38.212 V15.2.0 §7.2；LS/ZF是项目接收算法。链路为完整Rx时域信号→已知同步补偿→OFDM→时频OCC联合LS估计→ZF→逆层映射→QAM软解映射/解扰→DL-SCH/LDPC/TB CRC。

| 字段 | 含义、范围、示例 |
|---|---|
| resource | NRPDSCH，1～4层和DMRS配置，不含实际TB |
| n_bits | 期待TBS，整数16..8424、字节对齐且符合单码块容量，例256 |
| target_code_rate=.5 | 与发送一致的MCS目标R，0.0001..0.95，决定BG选择 |
| redundancy_version=0 | 当前接收RV0..3 |
| carrier_frequency_hz=0 | 有限非负载频Hz，与发送一致 |
| max_iterations=30 | LDPC最大迭代次数1..1000 |
| plot_config=None | 可选NRPlotConfig，None禁用 |
| detection_threshold=.1 | DMRS联合拟合能量比门限0..1，严格大于才检测 |
| n_ref=None | 与发送一致的有限缓冲界，None取母码N |
| max_condition_number=1e8 | 每RB信道条件数上限，有限实数≥1 |

构造/`__post_init__`验证上述字段，要求cell.n_rx_antennas≥n_layers，明确拒绝欠定ZF。每层波形必须先经有效MIMO信道叠加到接收天线；接收机没有真实信道参数输入，只能用DMRS估计。

`receive(waveform,*,known_frequency_offset_hz=0,known_initial_phase_rad=0,known_delay_samples=0,cp_fraction=1,plotter=None)`要求有限complex[Rx,T]完整当前slot，形状严格匹配cell；已知CFO（Hz）/初相（rad）先取负反旋，再按整数采样点净延迟提前补偿；cp_fraction为0..1的CP内FFT窗比例；plotter为可选共享NRStagePlotter。同步量不是估计结果，错误输入抛校验异常。

每RB收集已用端口的所有DMRS位置，构造已知端口签名矩阵A。不占某CDM组位置的端口系数为0，其余保留真实Gold-QPSK及频域/时域OCC。不能把混合参考分别直接除以每个端口序列。联合LS假设每RB在整个分配时间内近似恒定；附加DMRS是联合观测，不表示已实现时变插值。

文档自编号PDSCH-MRX-1，参考上述固定端口规则，LS/ZF为项目算法：

$$
Y_b=H_bA_b^T+N_b,\quad \widehat H_b=Y_b(A_b^\dagger)^T,\quad
W_b=\widehat H_b^\dagger,\quad \widehat x_{b,t}=W_by_{b,t},\quad
\nu_{b,v}=\sum_r|W_{b,v,r}|^2.\tag{PDSCH-MRX-1}
$$

| 变量 | 含义、范围、单位、维度 |
|---|---|
| b | 分配内RB号，选择一个RB的估计问题；取值范围/约束：0..P−1；单位：零基索引；维度/类型：整数标量 |
| v | 空间层索引，选择待分离数据流；取值范围/约束：0..V−1；单位：零基索引；维度/类型：整数标量 |
| r | 接收分支索引，选择观测行；取值范围/约束：0..Rx−1；单位：零基索引；维度/类型：整数标量 |
| t | 当前RB内的数据RE序号，选择被均衡的点；取值范围/约束：0..当前RB数据RE数−1；单位：零基索引；维度/类型：整数标量 |
| A_b | RB b的已知多层DMRS签名矩阵，联合估计的设计矩阵；取值范围/约束：有限复数且列满秩才能分离端口；单位：归一化复幅度；维度/类型：complex[Q,V] |
| Q | RB b不同有效DMRS位置数量，决定观测长度；取值范围/约束：正整数且必须提供足够独立观测；单位：RE计数；维度/类型：整数标量 |
| Y_b | RB b接收DMRS观测，LS拟合的输入；取值范围/约束：有限复数；单位：归一化复幅度/复增益；维度/类型：complex[Rx,Q] |
| H_b | RB b各发送层到Rx的有效信道，ZF的输入；取值范围/约束：有限复数；单位：归一化复幅度/复增益；维度/类型：complex[Rx,V] |
| N_b | RB b参考观测中的噪声项；取值范围/约束：有限复数；单位：归一化复幅度/复增益；维度/类型：complex[Rx,Q] |
| dagger | Moore–Penrose伪逆操作，构造最小二乘/ZF矩阵；取值范围/约束：按被作用矩阵计算；不是逐元素倒数；适用于矩阵，转置不改变元素值；单位：无量纲矩阵运算；维度/类型：输入[a,b]输出[b,a] |
| T | 普通转置操作，调整矩阵轴次序而不共轭；取值范围/约束：按被作用矩阵计算；不是逐元素倒数；适用于矩阵，转置不改变元素值；单位：无量纲矩阵运算；维度/类型：输入[a,b]输出[b,a] |
| W_b | RB b的ZF权矩阵，将Rx观测分离到各层；取值范围/约束：有限复数，病态/秩亏时均衡失败；单位：复均衡权；维度/类型：complex[V,Rx] |
| x_hat | 当前数据RE上的各层均衡估计，用于软解调；取值范围/约束：有限复数，受残余噪声和估计误差影响；单位：归一化复幅度；维度/类型：complex[V] |
| nu | 空间白噪声经ZF后的相对方差增益float[V]，软权重取1/nu；未标定绝对噪声 |

逐RB检查估计矩阵的秩和条件数，任一RB秩亏/非有限/超限则equalizer_ok=False，不解码TB。未坏RB可保留诊断层符号，但不把整体传输报成功。强信号秩亏可以detected=True同时crc_ok=False；零信号不译码。

逆层映射将complex[V,Nd]按每RE的Layer0..V-1轮流还原码字顺序。QAM max-log软解映射公式PDSCH-MRX-2为工程自编号：

$$
L_{t,v,i}\propto\frac1{\nu_{b(t),v}}\left[\min_{a\in\mathcal A_{i,1}}|\widehat x_{v,t}-a|^2-\min_{a\in\mathcal A_{i,0}}|\widehat x_{v,t}-a|^2\right].\tag{PDSCH-MRX-2}
$$

其中i=0..Qm-1是标记位；A_i,0/1是该位0/1的QAM候选complex[2^(Qm-1)]；x_hat为归一化层QAM点；b(t)为RE所在RB；L按RE、层、标记位展开为无量纲float[G]，解扰后正支持0。假设Rx空间白噪声/同方差，未估计噪声协方差。

| 输出字段 | 含义、单位、维度 |
|---|---|
| bits | 候选传输块比特，用于恢复原始业务；取值范围/约束：A个二进制位或未译码时None；单位：bit；维度/类型：list[A]/None |
| crc_ok | 传输块CRC是否通过，用于数据完整性判断；取值范围/约束：True/False；单位：逻辑值；维度/类型：bool |
| converged | LDPC校验是否收敛，用于诊断迭代译码；取值范围/约束：True/False；单位：逻辑值；维度/类型：bool |
| iterations | 实际译码迭代次数，用于诊断计算代价；取值范围/约束：0..max_iterations，未译码时0；单位：次数；维度/类型：整数标量 |
| detected | DMRS拟合检测是否通过，决定是否尝试接收；范围：True/False，不等于CRC通过；单位：无量纲；维度：bool |
| metric | DMRS拟合能量与实际参考能量比，用于门限检测；范围：0..1，零能量取0；单位：无量纲；维度：实标量 |
| equalizer_ok | 所有RB满列秩且条件数合格，bool |
| condition_numbers | float[P]，零/奇异信道可能inf，仅用于诊断 |
| equalized_symbols | 已恢复码字顺序complex[V*Nd] |
| layer_symbols | 每层均衡QAM，complex[V,Nd] |
| soft_bits | 已解扰且按码字顺序排列的float[G] |
| channel_matrix | DMRS估计complex[Rx,V,P]，含发送幅度beta |
| channel_estimates | 单层兼容旧形状[Rx,P]；多层为[Rx,V,P] |
| rx_grid | complex[Rx,slot符号数,载波子载波数] |

metric为实际DMRS位置联合拟合能量比，clip至0..1；未校准恒定虚警率。CRC失败仍可返回候选位，均衡失败为None，不能只凭detected判成功。

图阶段rx.channel（Rx/层轴展平）、rx.equalized（Layer图例）、rx.soft_bits及OFDM步骤，直接显示、不保存。不含频选/时间插值、MMSE/噪声白化、盲同步、动态预编码、5～8层/双码字或HARQ软合并。

```python
import numpy as np
from cell import NRCell
from pdsch import NRPDSCH, NRPDSCHTransmitter, NRPDSCHReceiver
r = NRPDSCH(NRCell(n_size_grid=12,n_rx_antennas=2),n_layers=2,n_prbs=2)
sent = NRPDSCHTransmitter(r).transmit([0,1]*64)
H = np.array([[1,.2j],[.1,1]],dtype=complex)
out = NRPDSCHReceiver(r,128).receive(H@sent['waveform'])
assert out['equalizer_ok'] and out['crc_ok'] and out['bits']==[0,1]*64
```

## 新手处理流程与资源图入口

接收端补偿给定同步量后OFDM解调。逐RB将各层DMRS的实际频域/时域OCC组成联合设计矩阵，LS估计[Rx,层,RB]信道；假定同一RB及分配时间内近似恒定。逐RB检查信道秩与条件数，用伪逆ZF分离各层；按发送顺序还原调制符号，计算距离软值、解扰、LDPC速率恢复/迭代译码并检查CRC。ZF不是MMSE，病态信道可能放大噪声；均衡失败不会仅凭DMRS检测通过就宣称业务恢复成功。

[NRPDSCH的时频位置、长度、配置变化及图例](NRPDSCH.md)与[统一坐标/采样点换算](../../documentation/channel_walkthrough.md)提供完整阅读顺序。当前类的输入输出单位、形状及异常约束以上文字段/API节为准。


## PT-RS 相位补偿

资源设置 `ptrs_config` 后，接收机以单个 DM-RS 符号的相位为零点，用每 RB 的 DM-RS 信道估计对同 RB 的 PT-RS 作匹配合并。将参考符号相位解缠、插值，首尾保持，再在生成软比特之前对均衡数据逐符号反旋。相邻有效参考的真实相位变化应小于 π rad。

`receive(..., correct_ptrs=False)` 可对同一段接收波形关闭反旋，仍按既定资源跳过 PT-RS RE。`ptrs_phase_rad` 是长度为 `cell.symbols_per_slot` 的实数数组，单位 rad。未配置或关闭时为 `None`。在阶段图中可选择 `rx.ptrs_phase` 查看估计。
