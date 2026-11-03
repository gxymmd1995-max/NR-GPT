# NRPUSCHReceiver

[源码](NRPUSCHReceiver.py)。完整时域接收→已知同步补偿→OFDM→每RB DMRS平坦信道估计/MRC→max-log QAM软解映射/解扰→NRULSCHCode速率恢复/LDPC/TB CRC。参考发送规则为TS38.211 V15.2.0 §6.3.1及§6.4.1.1；编码为TS38.212 V15.2.0 §6.2。接收算法为项目工程实现，不是规范指定的唯一算法。

| 字段 | 含义、范围、示例 |
|---|---|
| resource | NRPUSCH，不包含实际发送TB |
| n_bits | 期待TBS，字节对齐，16..8424且单码块可容纳；例256 |
| target_code_rate=.5 | MCS目标码率0.0001..0.95，用于BG选择，须与发送一致 |
| redundancy_version=0 | RV0..3，与接收到的码字一致 |
| carrier_frequency_hz=0 | 有限非负Hz，与发射一致 |
| max_iterations=30 | LDPC最大迭代1..1000 |
| plot_config=None | 可选NRPlotConfig，None禁用 |
| detection_threshold=.1 | DMRS拟合能量比门限，有限0..1，严格大于才检测 |

构造/`__post_init__`校验上述值。`receive(waveform,*,known_frequency_offset_hz=0,known_initial_phase_rad=0,known_delay_samples=0,cp_fraction=1,plotter=None)`要求有限complex[Rx,T]完整当前slot，形状严格匹配cell。CFO（Hz）、初相（rad）先取负反旋，再按整数采样点净延迟提前补偿；cp_fraction为CP内FFT窗比例0..1；可选共享plotter。参数均显式已知，不是盲同步估计结果。

每Rx每RB用6点DMRS共轭平均估计h，假设该RB在整个分配期间近似恒定平坦。对应每个数据RE跨Rx做MRC，除sum(abs(h)^2)，≤1e-20时置0。对每个QAM标记位，取其他位所有可能点的最小欧氏距离差，乘有效信道能量以形成可靠度加权软分数；之后按Gold符号解扰。没有独立噪声方差估计，soft_bits不是标定LLR。

文档自编号PUSCH-RX-1，参考上述固定版本发送规则；软解映射为工程max-log算法：

$$
\widehat h_{r,b}=\frac16\sum_{q=0}^{5}Y^{\rm DMRS}_{r,b,q}R_{b,q}^{*},\quad
\widehat d_t=\frac{\sum_r\widehat h_{r,b(t)}^{*}Y_{r,t}}{W_t},\quad W_t=\sum_r|\widehat h_{r,b(t)}|^2,
\quad L_{t,i}\propto W_t\left[\min_{a\in\mathcal A_{i,1}}|\widehat d_t-a|^2-\min_{a\in\mathcal A_{i,0}}|\widehat d_t-a|^2\right].\tag{PUSCH-RX-1}
$$

| 变量 | 含义、范围、单位与维度 |
|---|---|
| r、b、q、t、i | Rx、资源RB、DMRS点、数据RE、调制位索引；0..Rx-1、0..P-1、0..5、0..Nd-1、0..Qm-1 |
| Y_DMRS、R | 接收/参考DMRS，complex[Rx,P,6]/complex[P,6]，归一化幅度 |
| h_hat、Y、d_hat | 信道估计[Rx,P]、数据RE[Rx,Nd]、均衡数据[Nd]，complex归一化幅度 |
| b(t)、W | RE对应RB索引、有效信道能量；int[Nd]、float[Nd] |
| A_i,0/1 | 该标记位为0/1的QAM候选集合，complex[2^(Qm-1)]，平均能量归一化 |
| L | 无量纲软可靠性，解扰后展开float[G]，正值支持0 |

返回dict：bits为A位list，未检测时None；crc_ok严格bool，要求LDPC收敛且TB CRC通过；converged为LDPC校验状态；iterations为迭代次数，未检测0；detected为bool；metric为DMRS拟合能量比0..1；equalized_symbols为complex[Nd]；soft_bits为float[G]；channel_estimates为complex[Rx,P]；rx_grid为complex[Rx,slot符号数,载波子载波数]。

检测指标为6*sum(abs(h)^2)/sum(abs(received_dmrs)^2)，clip到0..1；零输入不译码，避免全零码字CRC偶然通过。检测、LDPC收敛和TB CRC是不同状态。某些RV单独接收时即使无噪仍可能因缺少系统位而不收敛；未实现跨次HARQ合并，失败时不会强制报成功。

绘图rx.channel、rx.equalized、rx.soft_bits及OFDM内部步骤，只显示不保存。首版不含频选插值/时间跟踪、盲同步、MIMO均衡、多码块、UCI/PTRS或HARQ软合并。

```python
from cell import NRCell
from pusch import NRPUSCH, NRPUSCHTransmitter, NRPUSCHReceiver
r = NRPUSCH(NRCell(n_size_grid=12), n_symbols=12)
wave = NRPUSCHTransmitter(r).transmit([0,1]*128)['waveform']
out = NRPUSCHReceiver(r,256).receive(wave)
assert out['crc_ok'] and out['bits'] == [0,1]*128
```
