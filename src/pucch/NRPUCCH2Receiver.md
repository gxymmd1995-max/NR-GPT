# NRPUCCH2Receiver

[源码](NRPUCCH2Receiver.py)：已知同步补偿→OFDM→DMRS估计→MRC→QPSK软分数→解扰→公共小块/Polar译码。参考发送依据TS38.211 V15.2.0 §6.3.2.5/§6.4.1.3.2；码字依据TS38.212 V15.2.0 §5.3.3.3、§5.4.3。信道估计、检测和ML是项目算法，不是3GPP强制接收机。

| 字段 | 含义、范围、示例 |
|---|---|
| resource | NRPUCCH2资源，不包含实际发送比特 |
| n_bits=3 | 原始UCI长度整数3..1706，且含CRC码率≤0.6，例7 |
| carrier_frequency_hz=0 | 有限非负Hz，与发射一致 |
| detection_threshold=.1 | DMRS拟合功率比门限，有限0..1，严格大于才检测 |
| plot_config=None | 可选NRPlotConfig，None关闭 |

自动构造/`__post_init__`验证资源、位数、码率、载频、门限和绘图配置。`receive(waveform,*,known_frequency_offset_hz=0,known_initial_phase_rad=0,known_delay_samples=0,cp_fraction=1,plotter=None)`：waveform为有限complex[Rx,T]完整slot，Rx/T严格等于cell；CFO有限Hz、初相有限rad先取负补偿，然后按整数采样点known_delay_samples提前以补偿净延迟；cp_fraction为0..1的CP内FFT窗位置。以上是显式已知同步量，不是估计结果；可选共享plotter延迟统一show。非法输入抛对应校验异常。

每符号每RB的4个DMRS估计一个平坦复增益，不跨符号合并信道，也不实现频率选择性插值。F2-RX-1为本文工程自编号，参考上述发送/编码章节：

$$
\widehat h_{r,s,b}=\frac14\sum_{q=0}^{3}Y^{\mathrm{DMRS}}_{r,s,b,q}R^*_{s,b,q},\quad
v_{s,b,n}=\sum_r\widehat h^*_{r,s,b}Y^{\mathrm{data}}_{r,s,b,n},\quad
\widehat d_{s,b,n}=\frac{v_{s,b,n}}{\sum_r|\widehat h_{r,s,b}|^2}.\tag{F2-RX-1}
$$

| 变量 | 含义、范围、单位与维度 |
|---|---|
| r、s、b、q、n | Rx、资源符号、资源RB、DMRS点、数据点索引；分别0..Rx-1、0..L-1、0..P-1、0..3、0..7 |
| Y_DMRS、R | 接收DMRS complex[Rx,L,P,4]、参考complex[L,P,4]；归一化幅度 |
| Y_data | 接收数据complex[Rx,L,P,8]，归一化幅度 |
| h_hat | 有效信道增益，含beta，complex[Rx,L,P] |
| v、d_hat | MRC未归一化投影、归一化QPSK点，complex[L,P,8] |
| soft_bits | 按RE顺序交织v实部/虚部，再乘解扰符号；float[E]，正值支持0 |

分母≤1e-20时均衡输出0。soft_bits与等白噪声假设下LLR成比例，未估计噪声方差，因此不称为标定LLR。小块ML译码前将重复码位软值相加；Polar通过NRUCICode反速率匹配并PC约束SC译码，输出CRC状态。DMRS指标为4*sum(abs(h)^2)/sum(abs(received_dmrs)^2)，clip到0..1；零能量指标0。该指标不是CRC，不保证数据可靠性，也未校准纯噪声虚警率。

输出dict：detected严格bool；bits为K位list或未检测None；metric无量纲实标量；soft_bits为float[E]；equalized_symbols为complex[L,P,8]；channel_estimates为complex[Rx,L,P]；rx_grid为complex[Rx,slot符号数,载波子载波数]。复幅度均归一化。

图阶段rx.channel_estimates、rx.equalized_constellation、rx.soft_bits及OFDM内部步骤，只显示不保存。边界：无CRC辅助SCL、盲同步、任意多用户联合均衡、强频率选择性均衡或HARQ/SR/CSI语义解析。

```python
from cell import NRCell
from pucch import NRPUCCH2, NRPUCCH2Transmitter, NRPUCCH2Receiver
r = NRPUCCH2(NRCell(n_size_grid=12), n_prbs=3)
wave = NRPUCCH2Transmitter(r).transmit([1,0,1])['waveform']
assert NRPUCCH2Receiver(r,3).receive(wave)['bits'] == [1,0,1]
```

当前公共接口：NRUCICode按A自动选择小块码或Polar，不调用LDPC或经典RM替代标准小块基矩阵。接收增加crc_ok：Polar为bool，小块/未检测为None；CRC失败仍返回判决位，detected只表示信号检测，不表示CRC通过。完整链路见NRPUCCH2_Polar_demo.py。
