# NRPUSCHReceiver：多层DMRS联合估计与ZF均衡

[源码](NRPUSCHReceiver.py)。固定发送依据TS38.211 V15.2.0 §6.3.1/§6.4.1.1及表6.3.1.3-1、6.4.1.1.3-1～5，编码依据TS38.212 V15.2.0 §6.2；LS/ZF是项目接收算法。链路为完整Rx时域信号→已知同步补偿→OFDM→时频OCC联合LS估计→ZF→逆层映射→QAM软解映射/解扰→UL-SCH/LDPC/TB CRC。

| 字段 | 含义、范围、示例 |
|---|---|
| resource | NRPUSCH，1～4层和DMRS配置，不含实际TB |
| n_bits | 期待TBS，整数16..8424、字节对齐且符合单码块容量，例256 |
| target_code_rate=.5 | 与发送一致的MCS目标R，0.0001..0.95，决定BG选择 |
| redundancy_version=0 | 当前接收RV0..3 |
| carrier_frequency_hz=0 | 有限非负载频Hz，与发送一致 |
| max_iterations=30 | LDPC最大迭代次数1..1000 |
| plot_config=None | 可选NRPlotConfig，None禁用 |
| detection_threshold=.1 | DMRS联合拟合能量比门限0..1，严格大于才检测 |
| max_condition_number=1e8 | 每RB信道条件数上限，有限实数≥1 |

构造/`__post_init__`验证上述字段，要求cell.n_rx_antennas≥n_layers，明确拒绝欠定ZF。每层波形必须先经有效MIMO信道叠加到接收天线；接收机没有真实信道参数输入，只能用DMRS估计。

`receive(waveform,*,known_frequency_offset_hz=0,known_initial_phase_rad=0,known_delay_samples=0,cp_fraction=1,plotter=None)`要求有限complex[Rx,T]完整当前slot，形状严格匹配cell；已知CFO（Hz）/初相（rad）先取负反旋，再按整数采样点净延迟提前补偿；cp_fraction为0..1的CP内FFT窗比例；plotter为可选共享NRStagePlotter。同步量不是估计结果，错误输入抛校验异常。

每RB收集已用端口的所有DMRS位置，构造已知端口签名矩阵A。不占某CDM组位置的端口系数为0，其余保留真实Gold-QPSK及频域/时域OCC。不能把混合参考分别直接除以每个端口序列。联合LS假设每RB在整个分配时间内近似恒定；附加DMRS是联合观测，不表示已实现时变插值。

文档自编号PUSCH-MRX-1，参考上述固定端口规则，LS/ZF为项目算法：

$$
Y_b=H_bA_b^T+N_b,\quad \widehat H_b=Y_b(A_b^\dagger)^T,\quad
W_b=\widehat H_b^\dagger,\quad \widehat x_{b,t}=W_by_{b,t},\quad
\nu_{b,v}=\sum_r|W_{b,v,r}|^2.\tag{PUSCH-MRX-1}
$$

| 变量 | 含义、范围、单位、维度 |
|---|---|
| b、v、r、t | RB、层、Rx、数据RE索引；0..P-1、0..V-1、0..Rx-1、每RB有效RE范围 |
| A_b、Q | 已知DMRS签名complex[Q,V]、实际参考位置数Q；不含纯保留无发送的CDM组 |
| Y_b、H_b、N_b | 参考观测[Rx,Q]、有效信道[Rx,V]、参考噪声[Rx,Q]，complex归一化幅度 |
| dagger、T | Moore–Penrose伪逆、普通转置；A已包含发送参考相位 |
| W_b、x_hat | ZF矩阵[V,Rx]、层均衡符号[V]，complex |
| nu | 空间白噪声经ZF后的相对方差增益float[V]，软权重取1/nu；未标定绝对噪声 |

逐RB检查估计矩阵的秩和条件数，任一RB秩亏/非有限/超限则equalizer_ok=False，不解码TB。未坏RB可保留诊断层符号，但不把整体传输报成功。强信号秩亏可以detected=True同时crc_ok=False；零信号不译码。

逆层映射将complex[V,Nd]按每RE的Layer0..V-1轮流还原码字顺序。QAM max-log软解映射公式PUSCH-MRX-2为工程自编号：

$$
L_{t,v,i}\propto\frac1{\nu_{b(t),v}}\left[\min_{a\in\mathcal A_{i,1}}|\widehat x_{v,t}-a|^2-\min_{a\in\mathcal A_{i,0}}|\widehat x_{v,t}-a|^2\right].\tag{PUSCH-MRX-2}
$$

其中i=0..Qm-1是标记位；A_i,0/1是该位0/1的QAM候选complex[2^(Qm-1)]；x_hat为归一化层QAM点；b(t)为RE所在RB；L按RE、层、标记位展开为无量纲float[G]，解扰后正支持0。假设Rx空间白噪声/同方差，未估计噪声协方差。

| 输出字段 | 含义、单位、维度 |
|---|---|
| bits、crc_ok、converged、iterations | A位候选list或None；TB CRC/LDPC校验bool；失败无译码时迭代0 |
| detected、metric | DMRS参考检测bool、联合拟合能量/实际能量比0..1，独立于均衡/CRC |
| equalizer_ok | 所有RB满列秩且条件数合格，bool |
| condition_numbers | float[P]，零/奇异信道可能inf，仅用于诊断 |
| equalized_symbols | 已恢复码字顺序complex[V*Nd] |
| layer_symbols | 每层均衡QAM，complex[V,Nd] |
| soft_bits | 已解扰且按码字顺序排列的float[G] |
| channel_matrix | DMRS估计complex[Rx,V,P]，含发送幅度beta |
| channel_estimates | 单层兼容旧形状[Rx,P]；多层为[Rx,V,P] |
| rx_grid | complex[Rx,slot符号数,载波子载波数] |

metric为实际DMRS位置联合拟合能量比，clip至0..1；未校准恒定虚警率。CRC失败仍可返回候选位，均衡失败为None，不能只凭detected判成功。

图阶段rx.channel（Rx/层轴展平）、rx.equalized（Layer图例）、rx.soft_bits及OFDM步骤，直接显示、不保存。不含频选/时间插值、MMSE/噪声白化、盲同步、动态预编码、超过4层/多码字或HARQ软合并。

```python
import numpy as np
from cell import NRCell
from pusch import NRPUSCH, NRPUSCHTransmitter, NRPUSCHReceiver
r = NRPUSCH(NRCell(n_size_grid=12,n_rx_antennas=2),n_layers=2,n_prbs=2)
sent = NRPUSCHTransmitter(r).transmit([0,1]*64)
H = np.array([[1,.2j],[.1,1]],dtype=complex)
out = NRPUSCHReceiver(r,128).receive(H@sent['waveform'])
assert out['equalizer_ok'] and out['crc_ok'] and out['bits']==[0,1]*64
```
