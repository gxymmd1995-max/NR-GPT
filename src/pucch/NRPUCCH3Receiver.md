# NRPUCCH3Receiver

[源码](NRPUCCH3Receiver.py)。已知同步→OFDM→DMRS估计→MRC→单位化IDFT解扩→调制软解映射/解扰→公共UCI译码及CRC。发送依据TS38.211 V15.2.0 §6.3.2.6及§6.4.1.3.3，编码依据TS38.212 V15.2.0 §6.3.1；接收算法为项目实现，不是规范指定的唯一算法。

| 字段 | 含义、范围、示例 |
|---|---|
| resource | NRPUCCH3，接收配置不含实际发送位 |
| n_bits=3 | 期待UCI长度3..1706，例32；含CRC码率≤0.6 |
| carrier_frequency_hz=0 | 有限非负Hz，须与发射一致 |
| detection_threshold=.1 | DMRS拟合能量比门限，有限0..1，严格大于才检测 |
| plot_config=None | 可选NRPlotConfig，None禁用 |

构造/`__post_init__`校验上述值。`receive(waveform,*,known_frequency_offset_hz=0,known_initial_phase_rad=0,known_delay_samples=0,cp_fraction=1,plotter=None)`：有限complex[Rx,T]，必须为当前cell完整slot；先以负CFO（Hz）/初相（rad）反旋，再按已知净延迟整数采样点提前；cp_fraction为0..1的CP内FFT窗比例；plotter为可选共享绘图器。同步参数均显式已知，未做盲估计。非法输入抛校验异常。

每一跳的全部DMRS、频率点平均估计每Rx平坦增益h，假设同跳内时间/频率近似恒定。每数据符号进行跨Rx最大比合并，再对M=12P个频率点作单位化IDFT；均衡输出除以sum(abs(h)^2)，≤1e-20时输出0。QPSK使用实/虚投影，π/2-BPSK先去交替相位再投影，均在连续调制符号索引上解映射。软分数使用未归一化MRC值，以保持支路/跳的可靠度权重；白噪声假设下仅与LLR成比例，无独立噪声方差标定。

工程自编号F3-RX-1，参考上述发送章节：

$$
v_{s,k}=\sum_r\widehat h_{r,a(s)}^*Y_{r,s,k},\quad
q_{s,m}=\frac1{\sqrt M}\sum_{k=0}^{M-1}v_{s,k}e^{j2\pi mk/M}.\tag{F3-RX-1}
$$

| 变量 | 含义、范围、单位、维度 |
|---|---|
| r、s、k、m | Rx、数据符号、频率/IDFT输出索引；范围0..Rx-1、0..S-1、0..M-1 |
| a(s) | 当前数据符号的跳号0/1，标量 |
| h_hat | DMRS估计有效信道，含beta；complex[Rx]每跳 |
| Y、v、q | 接收频域数据[Rx,S,M]、MRC结果[S,M]、IDFT结果[S,M]，归一化复幅度 |
| M | 每数据符号子载波数12P，整数标量 |

检测指标为每跳平坦DMRS重建能量/DMRS接收总能量，clip到0..1。它只表示参考信号一致性，不是CRC，也不保证恒定虚警率；detected与crc_ok必须区分。返回dict：bits为A位list或未检测None；crc_ok为Polar的bool或小块/未检测None；detected为bool；metric无量纲实数；soft_bits为float[E]；equalized_symbols为complex[S*M]；channel_estimates为complex[S,Rx]（按每个数据符号重复对应跳估计）；rx_grid为complex[Rx,slot符号数,载波子载波数]。

绘图rx.idft_constellation、rx.soft_bits及OFDM阶段；只显示不保存。未实现频率选择性均衡、DMRS时间插值、盲同步、联合多用户接收或SCL；SC在低SNR下性能有限，CRC失败不能当成功传输。

```python
from cell import NRCell
from pucch import NRPUCCH3, NRPUCCH3Transmitter, NRPUCCH3Receiver
r = NRPUCCH3(NRCell(n_size_grid=24), n_prbs=3)
wave = NRPUCCH3Transmitter(r).transmit([0,1]*16)['waveform']
out = NRPUCCH3Receiver(r,32).receive(wave)
assert out['bits'] == [0,1]*16 and out['crc_ok']
```
