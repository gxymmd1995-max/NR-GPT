# NRPUCCH1Receiver

[源码](NRPUCCH1Receiver.py)。接收经过真实时域信道的完整slot波形，已知同步补偿→OFDM→去序列和OCC→DMRS估计→MRC→1/2bit硬判决。发送基线见[资源文档](NRPUCCH1.md)；以下信道估计/检测是项目算法，不是3GPP强制接收机。

假设每UE每跳每Rx在时间和12子载波内近似恒定复增益。未实现盲同步、频率选择性均衡、信道时间插值、多用户联合检测、SR资源选择。当前DTX门限不是恒定虚警保证，近远效应/强干扰可造成误检。

| 字段 | 含义、范围、示例 |
|---|---|
| resource | 必须NRPUCCH1，不包含实际发送比特 |
| n_bits=1 | 期待UCI位数，整数1/2；例2 |
| carrier_frequency_hz=0 | 有限非负载频Hz，须与发射机一致 |
| detection_threshold=.1 | DMRS拟合功率/接收DMRS总功率的门限，有限0..1，严格大于才检测 |
| plot_config=None | 可选NRPlotConfig，None关闭 |

构造及`__post_init__`校验配置。`receive(waveform,*,known_frequency_offset_hz=0,known_initial_phase_rad=0,known_delay_samples=0,cp_fraction=1,plotter=None)`不修改输入：waveform为有限complex[Rx,T]，Rx和T必须等于cell配置；已知频偏Hz、初相rad先取负补偿，再提前known_delay_samples个采样点补偿净延迟（整数，正数提前）；cp_fraction是FFT窗在CP中的比例0..1；plotter是可选共享NRStagePlotter。这些是显式已知量，不是估计结果。输入形状错误抛ValueError，数值范围沿用NRChannel/NROFDM检查。

以下F1-RX-1为本文工程自编号，发送参考依据TS38.211 V15.2.0 §6.3.2.4、§6.4.1.3.1：

$$
p_{r,l}=\frac1{12}\sum_{n=0}^{11}Y_{r,l,n}R_{l,n}^{*},\quad
\widehat h_{r,a}=\operatorname{mean}_{l\in D_a}p_{r,l},\quad
\widehat d=\frac{\sum_{a,r}\sum_{l\in U_a}\widehat h_{r,a}^{*}p_{r,l}}{\sum_{a,r}|\widehat h_{r,a}|^2|U_a|}.\tag{F1-RX-1}
$$

| 变量 | 含义、范围、单位、维度 |
|---|---|
| Y | 接收F1资源RE，作为解扩输入；取值范围/约束：有限复数；单位：归一化复幅度；维度/类型：complex[Rx,L,12] |
| R | 含循环移位及时域OCC的本地单位模参考；取值范围/约束：每点模长1；单位：归一化复幅度；维度/类型：complex[L,12] |
| r | 接收支路号，选择天线；取值范围/约束：0..Rx−1；单位：零基索引；维度/类型：整数标量 |
| l | 资源相对符号号，选择投影；取值范围/约束：0..L−1；单位：零基索引；维度/类型：整数标量 |
| n | RB内子载波号，沿频率解扩；取值范围/约束：0..11；单位：零基索引；维度/类型：整数标量 |
| a | 当前跳段号，分段估计信道；取值范围/约束：无跳频仅0，有跳频0/1；单位：零基索引；维度/类型：整数标量 |
| D_a | 跳a中DMRS符号集合，用于信道估计；取值范围/约束：本跳的资源内偶数符号，至少1项；单位：资源内符号索引；维度/类型：一维整数索引集合 |
| U_a | 跳a中数据符号集合，用于数据合并；取值范围/约束：本跳的资源内奇数符号，至少1项；单位：资源内符号索引；维度/类型：一维整数索引集合 |
| p | 去序列/OCC后的复投影，complex[Rx,L]，归一化幅度 |
| h_hat | 每跳每Rx有效信道估计，含发送beta，complex[跳数,Rx] |
| d_hat | MRC后复标量，理想为单位能量BPSK/QPSK符号 |

分母小于等于1e-20时输出零并判未检测。检测指标为DMRS估计重建能量除以接收DMRS能量，clip到0..1，零能量为0；实部符号判第0位，2bit时虚部符号判第1位。指标主要检测DMRS一致性，不保证数据可靠性。

返回字段：detected为bool；bits为1/2位list或未检测时None；metric为无量纲实标量；equalized_symbol为复标量；channel_estimates为complex[跳数,Rx]；rx_symbols为complex[Rx,L,12]；rx_grid为complex[Rx,slot符号数,载波子载波数]。复数幅度均归一化，无绝对瓦特/dBm标定。

绘图rx.despread展示每符号复投影，rx.equalized_constellation展示均衡后的UCI点；加上OFDM各阶段，只显示不保存。

```python
from cell import NRCell
from pucch import NRPUCCH1, NRPUCCH1Transmitter, NRPUCCH1Receiver
r = NRPUCCH1(NRCell(n_size_grid=6))
wave = NRPUCCH1Transmitter(r).transmit([0,1])['waveform']
assert NRPUCCH1Receiver(r,2).receive(wave)['bits'] == [0,1]
```

## 新手处理流程与资源图入口

先OFDM解调和提取12点序列，乘包含循环移位/OCC的参考共轭并沿频率平均，得到每符号解扩值。每个跳段用DMRS估计每Rx复增益，再跨该段数据符号和天线合并、均衡，按BPSK实部或QPSK实虚部符号判比特。接收机假设跳段内信道足够稳定，不是任意快时变多径估计器。

[NRPUCCH1的时频位置、长度、配置变化及图例](NRPUCCH1.md)与[统一坐标/采样点换算](../../documentation/channel_walkthrough.md)提供完整阅读顺序。当前类的输入输出单位、形状及异常约束以上文字段/API节为准。
