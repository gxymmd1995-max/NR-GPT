# NRPUCCH0Receiver：Format 0时域接收与DTX检测

[源码](NRPUCCH0Receiver.py)接收完整slot时域信号，通过已知同步补偿、OFDM解调、已配置资源提取和合法UCI候选相关得到HARQ-ACK/SR。输入是经过信道的波形，不能把原发送网格作为接收输入。

发送参考固定 **TS38.211 V15.2.0 §6.3.2.2/3**；UCI候选来自 **TS38.213 V15.3.0 §9.2.3、§9.2.4、§9.2.5.1**。非相干检测、DTX门限和候选平分规则为项目算法，下面RX0-1是本文自编号，非规范原公式。

## 接收假设与边界

资源位置、HARQ位数、是否为SR机会由调度配置给出，接收机不从时域盲猜这些信息。F0没有独立DMRS，12个频率点内假定信道近似平坦，每个OFDM符号/跳段/接收支路可有独立未知复增益。跨符号以相关功率非相干合并，不要求不同Rx或跳段相位相同。不输出独立信道估计、盲频偏/定时估计或可靠SNR估计。

支持显式已知CFO/初相/整数时延补偿；补偿参数不是接收机估计结果。多径引起的RB内强频选、未知大残余CFO/TA、多用户同资源干扰会降低检测能力；当前不做联合用户检测或空间干扰白化。有限捕获窗口丢失的样点不能通过补零恢复，示例在资源后保留空符号。

## 每个字段和方法

每个实例检测一个已配置UE；多个实例可以接收同一份混合波形，通过互不重叠的循环移位候选集合分离用户，见[三用户示例](../../examples/pucch/README.md#三用户循环移位复用)。这属于逐用户相关检测，不是联合估计或SIC。

### 循环移位分配校验

`validate_cyclic_shift_group(receivers)`为静态方法。输入为非空字典，例如`{'UE0': rx0, 'UE1': rx1}`；键必须是非空白字符串，值必须是本类实例。各实例必须具有相同cell、prb、start_symbol、n_symbols、hopping_id、group_hopping、second_hop_prb，以保证公共时频位置、根序列及逐符号跳变。

返回`dict[str,list[int]]`，每个列表为该UE所有合法UCI候选对应的`(initial_cyclic_shift + m_cs) % 12`，已排序去重，单位为循环移位索引，范围0..11。公共逐符号n_cs尚未加入；它对全部UE作相同模12旋转，不改变集合相交关系。空输入、错误类型、资源不一致或任意用户间候选集合相交均抛ValueError，错误中指出冲突用户与移位。此接口只校验这一类CDM分配，不是通用多用户调度器。

内部`_hypotheses()`无参数，返回`list[tuple[tuple[int,...],int|None]]`：每项为HARQ位tuple与SR候选，供检测和分配校验共用。其数量由n_harq_ack_bits和sr_enabled确定，不读取实际发送比特。

多用户时RX0-1分母包含全部UE的接收能量，因此单个UE得分通常下降。示例显式设置detection_threshold=0.15；单用户默认值不变。该工程门限不保证任意功率差、用户数或信道下的虚警/漏检性能。不同用户残余CFO、时延差及RB内频率选择性会破坏理想正交性。

冻结slots dataclass，无隐藏缓存/类常量。

| 字段 | 含义、范围和单位 | 示例 |
|---|---|---|
| resource | 必须NRPUCCH0，含当前slot和资源配置 | 与发送端使用相同配置，不携带实际发送的HARQ/SR值 |
| n_harq_ack_bits=1 | 本次期待HARQ位数，Python int 0/1/2 | 2 |
| sr_enabled=False | 是否期待该资源承载SR，严格bool | True表示搜索负/正SR；不是已知实际发送的SR值 |
| carrier_frequency_hz=0 | 有限非负RF载频，Hz | 与发射机相同，3500000123 |
| detection_threshold=None | 无量纲归一化相关功率门限 | None解析为1符号0.49、2符号0.42；可配置有限实数0..1；严格大于才检测 |
| 自动__init__、__post_init__ | 校验字段并解析门限；HARQ位数0且不期待SR时报ValueError | `NRPUCCH0Receiver(resource,2,True)` |
| receive(waveform,*,known_frequency_offset_hz=0,known_initial_phase_rad=0,known_delay_samples=0,cp_fraction=1) | 完整当前slot波形→下表结果，输入不修改 | 详见参数表 |

默认门限与当前Toolbox常用1/2符号默认值一致，但未声称恒定虚警率或空口性能保证；可按接收条件调整。

| receive参数 | 含义 | 范围/单位/维度 |
|---|---|---|
| waveform | 经过信道的复时域波形 | 有限complex可转换[Rx,T]，Rx严格等于cell.n_rx_antennas，T严格等于cell.samples_per_slot |
| known_frequency_offset_hz | 已知需要消除的CFO；先施加负频偏 | 有限实数，严格-Fs/2<CFO<Fs/2，Hz标量 |
| known_initial_phase_rad | 与已知CFO匹配的初相，先反旋转 | 任意有限实数，rad标量；连续样点原点为本slot输入第0点 |
| known_delay_samples | 已知要消除的净传播延迟，正数提前输入波形 | Python int，[-T,T]，sample标量；不是TA命令字段 |
| cp_fraction | FFT起点在CP中的比例 | 有限实数0..1，默认1；与NROFDM定义一致，自动恢复提前窗相位 |

调用顺序：先CFO/初相逆旋转，再按已知delay非循环移位，接着OFDM解调。若信道先TA提前2点再传播延迟5点，此参数应为净延迟3点。

## 候选与判决公式

对于每个合法候选h，参考序列每符号12点、每点模长1：

$$
z_{h,r,s}=\sum_{n=0}^{11}y_{r,s,n}x^*_{h,s,n},\quad
M_h=\frac{\sum_{r,s}|z_{h,r,s}|^2}{12\sum_{r,s,n}|y_{r,s,n}|^2},\quad
\widehat h=\arg\max_h M_h. \tag{RX0-1}
$$

| 变量 | 含义 | 范围/单位 | 维度与求和轴 |
|---|---|---|---|
| h、H | UCI候选号、候选数量 | HARQ1/2且无SR时H2/4，有SR时H4/8；SR-only仅正SR参考，H1 | 整数索引/计数 |
| r、s、n | Rx支路号、F0资源符号号、RB内频率点号 | r0..Rx-1，s0..S-1，n0..11 | 三个零基整数 |
| y | 已配置RE上的接收网格值 | 有限归一化复幅度，含噪声/干扰 | [Rx,S,12] |
| x、星号* | 候选参考、复共轭 | 模长1；本式*表示共轭，不是卷积 | 参考[S,12]，向Rx广播 |
| z | 每Rx/符号的相关复投影 | 有限复数，归一化复幅度 | 每候选[Rx,S]；只沿n先求和 |
| M | 相关功率归一化得分 | 理论0..1；浮点误差clip至该范围 | 每候选实标量；分子按Rx/S求平方模和，分母按所有Rx/S/12点求功率和 |
| h_hat、门限 | 得分最高候选及检测界限 | 总能量>0且max(M)>threshold才检测；平分保持枚举首项 | 候选索引、无量纲实标量 |

总能量0时所有得分定义为0并判DTX，不除0。候选按HARQ位tuple的00/01/10/11次序及SR0/1次序枚举；这不改变标准m_cs映射表。不同符号的z可能反相，先平方模再合并避免相干抵消。

## 输出字典

| 字段 | 含义/单位/维度 |
|---|---|
| detected、status | bool及'detected'/'dtx'；未检测到不等同于解出NACK |
| harq_ack | 检测成功为按发送位序的Python list，SR-only正SR为[]；DTX为None |
| sr | 未配置SR为None；成功检测为0/1；SR-only未检测为0；有HARQ但DTX时None |
| m_cs | 成功候选UCI移位偏移int；DTX为None |
| metric | 最大无量纲相关功率，0..1；DTX时也提供观察到的最大值 |
| detection_threshold | 已解析的当前门限，实标量 |
| candidates | H个字典，每个含harq_ack、sr、m_cs、metric；包含所有检测假设 |
| resource_power | 原始接收参考RE的平方模平均，归一化功率/RE/Rx；含噪声/干扰，不叫用户RSRP或SNR |
| rx_symbols | 新complex128[Rx,S,12]接收RE副本 |
| rx_grid | OFDM解调后complex128[Rx,L,K]接收网格 |
| synchronization | 字符串说明只使用显式已知补偿，不宣称盲同步 |

未检测SR-only时sr=0仅是当前SR机会的接收判决，不能从纯噪声恢复一个“负SR波形”。绝对零发送经基于自身SNR加噪会仍为零；演示使用活动参考的SNR来校准负SR背景噪声，见[示例README](../../examples/pucch/README.md)。

## 可运行时域例子

```python
from cell import NRCell
from channel import NRChannel
from pucch import NRPUCCH0,NRPUCCH0Transmitter,NRPUCCH0Receiver

cell=NRCell(n_size_grid=24,n_rx_antennas=1)
r=NRPUCCH0(cell,start_symbol=10,n_symbols=2,second_hop_prb=20)
sent=NRPUCCH0Transmitter(r).transmit([1,0],sr=1)
received,noise=NRChannel(cell).add_awgn(sent['waveform'],snr_db=5,seed=42)
result=NRPUCCH0Receiver(r,n_harq_ack_bits=2,sr_enabled=True).receive(received)
assert result['harq_ack']==[1,0] and result['sr']==1
```

[验证报告](../../documentation/validation/NRPUCCH0_validation.md)含真实Toolbox序列/波形/译码与独立MATLAB相关得分比对；这验证本项目检测算法，不等同于完整UE/gNB接收一致性认证。


## 交互绘图字段（不保存图片）

新增字段`plot_config: NRPlotConfig | None=None`，None默认关闭，错误配置类型TypeError。例：`NRPUCCH0Receiver(resource,plot_config=NRPlotConfig(enabled=True,stages=('rx.*',)))`。`receive(...,plotter=None)`新增仅关键字参数，传NRStagePlotter共享完整链路；此时由外部统一show，不在receive中单独显示。输出新增plot_stages字符串list；不改变数值输出和判决。

接收12阶段：rx.input_waveform、rx.cfo_corrected、rx.timing_corrected、rx.fft_windows、rx.fft_spectrum、rx.cropped_grid、rx.window_corrected_grid、rx.phase_corrected_grid、rx.extracted_symbols、rx.correlated_constellation、rx.candidate_metrics、rx.decision。频谱/网格同时看功率与B0相位；候选得分和检测门限无量纲。字段、选点限制和轴见[绘图配置](../diagnostics/NRPlotConfig.md)、[收集器](../diagnostics/NRStagePlotter.md)。


## 相关输出星座图与复数返回值

新增返回字段`correlation_symbols`为最佳候选的complex128[Rx,S]新数组，`candidate_correlation_symbols`为所有候选的complex128[H,Rx,S]新数组，候选顺序与candidates相同；S为PUCCH符号数1/2，H为合法UCI候选数，Rx为接收支路数。二者为按参考能量12归一化的相关值：c[h,r,s]=z[h,r,s]/12，其中z是RX0-1定义的12点复相关和；单位归一化复幅度，不是功率，也不反除发送beta或信道增益。依据仍为TS38.211 V15.2.0 §6.3.2.3发送参考，相关观测是项目接收处理，无新增协议公式号。

`rx.correlated_constellation`绘制最佳候选[Rx,S]的I/Q点，每个Rx用不同标记，S标签代表资源内符号号。平坦信道、无噪声且候选正确时，c约等于beta乘该Rx/符号的复信道系数；F0不具有QPSK固定判决星座，因此不会画虚假的固定比特点或强制旋到单位圆。DTX时仍可查看最佳候选的噪声投影，但标题明确标识DTX。开关与阶段筛选继续使用plot_config，关闭时复相关返回值仍可供后续处理。

```python
from diagnostics import NRPlotConfig
config=NRPlotConfig(enabled=True,stages=('rx.correlated_constellation',))
```
