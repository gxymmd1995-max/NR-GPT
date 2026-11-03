# NRPUCCH0Transmitter：Format 0时域发射机

[源码](NRPUCCH0Transmitter.py)组合[NRPUCCH0](NRPUCCH0.md)、NRGrid和[NROFDM](../common/NROFDM.md)，从HARQ-ACK/SR生成完整当前slot的时域信号。后续格式应各自实现发射机，复用公共OFDM与信道，不在F0中添加未实现格式开关。

序列/RE映射固定 **TS38.211 V15.2.0 §6.3.2.2/3**，OFDM/符号相位依据同版本 **§5.3.1/§5.4**。UCI移位表见[资源类](NRPUCCH0.md)。没有独立DMRS、信道、调度或物理天线预编码；这些由对应接收机/上层提供。

## 字段与方法

冻结slots dataclass，没有其他属性/常量/缓存。

| 字段/方法 | 用途、范围和例子 |
|---|---|
| resource | 必须NRPUCCH0，包含不可变NRCell和当前slot资源；`NRPUCCH0Transmitter(NRPUCCH0(cell))` |
| carrier_frequency_hz=0 | 有限非负载频Hz实标量，传NROFDM作NR逐符号相位补偿；不是CFO；例如3500000123 |
| 自动__init__、__post_init__ | 校验resource类型及NROFDM载频参数，错误TypeError/ValueError |
| transmit(harq_ack=(),sr=None,beta=1) | HARQ tuple/list/整数一维数组0..2位，SR为None/0/1，beta非负有限线性幅度；调用一次产生独立输出，不保存时钟或随机状态 |

输出为下表字典；类型/范围错误沿用资源与OFDM接口。

| 返回字段 | 意义 | 单位/维度 |
|---|---|---|
| waveform | 完整当前slot含CP和相位补偿的复波形 | 归一化复幅度，complex128[1,T]；T=cell.samples_per_slot |
| grid | 实际发送NRGrid对象，端口2000映射数组端口0 | 数据/标签[1,L,K]；L=12/14，K=12*n_size_grid |
| symbols | 未乘beta的原始序列，负SR-only为空 | 归一化复幅度，[12*S]或[0] |
| indices | 配置的所有资源坐标，即使DTX也可定位资源 | 零基[12*S,3]，列[端口,slot符号,载波局部k] |
| n_mapped_re | 本次实际写入的RE数 | 0或12*S，整数标量 |
| m_cs | UCI表给出的循环移位偏移 | int 0..11；DTX为None，不是初始m0或最终逐符号移位 |
| active | 当前UCI是否应发送波形 | bool；beta=0时active仍True，但波形为0 |

## 时域公式与单位

以下TX0-1为本文自编号的离散实现式，依据TS38.211 V15.2.0 §5.3.1/§5.4，单numerology的k0=0；IFFT归一化1/N是平台选择。

$$
x_l[n]=\frac{p_l}{N}\sum_{k=0}^{K-1}a_{k,l}\exp(j2\pi(k-K/2)n/N),\quad
p_l=\exp[-j2\pi f_0(t_{start,l}+N_{CP,l}T_c)].
$$

| 变量 | 含义 | 范围/单位 | 维度 |
|---|---|---|---|
| a、x | beta缩放后的网格、有效部分复时域信号 | 有限归一化复幅度 | a[1,L,K]；每符号x[1,N] |
| N、K、L、n、k、l | FFT长度、网格宽、符号数、样点/子载波/符号号 | N=cell.n_fft；K≤N；L12/14；0≤n<N，0≤k<K，0≤l<L | 计数/索引，整数标量 |
| f0、p_l | 载频、NR单位模相位 | f0≥0 Hz；p模长1，无量纲 | 标量、[L] |
| t_start_l、N_CP_l、Tc | CP起点相对子帧首、协议CP的Tc个数、基本时间单位 | 起点s；CP为Tc数；Tc=1/1966080000 s | 每符号标量/常量 |
| T、CP_samples_l | 完整slot样点数、逐符号CP采样点数 | T=sum(N+CP_samples_l)，不使用平均slot时长取整 | sample计数；整数标量/[L] |

NROFDM复制有效部分末尾CP_samples_l点作为前缀；不同slot的CP由NRCell精确计算。时域两个支路/多天线应由外部空间映射从单逻辑端口生成，不能把NRCell.n_tx_antennas当作本波形首轴。负SR-only输出全零[1,T]且网格不占用资源。

## 可运行示例

```python
from cell import NRCell
from common import NROFDM
from pucch import NRPUCCH0,NRPUCCH0Transmitter

cell=NRCell(n_size_grid=24)
resource=NRPUCCH0(cell,start_symbol=10,n_symbols=2)
sent=NRPUCCH0Transmitter(resource,3500000123).transmit([1,0],1,beta=.8)
assert sent['waveform'].shape==(1,cell.samples_per_slot)
assert sent['n_mapped_re']==24
assert NROFDM(cell,3500000123).demodulate(sent['waveform']).shape==(1,14,288)
```

[完整时域信道示例](../../examples/pucch/README.md)、[验证报告](../../documentation/validation/NRPUCCH0_validation.md)。


## 交互绘图字段（不保存图片）

新增字段`plot_config: NRPlotConfig | None=None`，None默认关闭；对象类型错误TypeError。`NRPUCCH0Transmitter(resource,plot_config=NRPlotConfig(enabled=True))`可直接显示发送阶段。`transmit(...,plotter=None)`新增仅关键字参数，传NRStagePlotter可与后续信道/接收共享记录；共享时忽略本类plot_config且不自行show，调用方统一显示。返回字典新增plot_stages，为截至该调用已记录的完整阶段名list。

发送阶段：tx.uci_shift、tx.base_sequence（同u零移位诊断基序列）、tx.cyclic_shift、tx.alpha、tx.mapped_grid、tx.symbol_phase、tx.phase_compensated_grid、tx.fft_spectrum、tx.ifft_useful、tx.cp_waveform。NROFDM内部记录实际阶段数组，关闭时不生成这些图窗。完整字段和轴见[NRPlotConfig](../diagnostics/NRPlotConfig.md)、[NRStagePlotter](../diagnostics/NRStagePlotter.md)。
