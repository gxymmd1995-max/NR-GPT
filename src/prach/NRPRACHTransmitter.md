# NRPRACHTransmitter：PRACH时域发射机

[源码](NRPRACHTransmitter.py)。固定TS38.211 V15.2.0 §6.3.3.1/§6.3.3.2及§5.3.2，使用NRPRACH的ZC/DFT、独立PRACH IFFT、周期重复和一次前缀，生成一个逻辑端口4000的实际基带波形。无需传输块、QAM或信道编码。

| 字段 | 含义、范围、单位、示例 |
|---|---|
| resource | 必须NRPRACH，已调度的一次时频机会；例NRPRACH(NRCell()) |
| plot_config=None | 可选NRPlotConfig；None禁用，例NRPlotConfig(enabled=True,channel='PRACH') |

构造/`__post_init__`检查资源和绘图配置。`transmit(preamble_index=0,beta=1,*,plotter=None)`：前导号整数0..63，beta为有限非负线性幅度、无量纲，例0.5代表幅度减半；plotter为可选共享NRStagePlotter。前导号由方法传入，可共享同一resource产生多个前导，便于多UE同一时机叠加。

本文自编号PRACH-TX-1，依据上述规范时序，归一化约定见[NRPRACH](NRPRACH.md)：

$$
w[0,s+i]=\begin{cases}
\beta z[(i-C_{CP})\bmod N],&0\le i<C_{CP}+RN,\\
0,&\text{outside active occasion}.
\end{cases}\tag{PRACH-TX-1}
$$

| 变量 | 含义、范围、单位与维度 |
|---|---|
| w、z | 单发送支路complex[1,T]、单有效周期complex[N]，归一化幅度 |
| s、i | 捕获数组中的CP起点、活动样点索引；s≥0，i=0..C_CP+RN-1，整数采样点 |
| C_CP、N、R | CP长度采样点、PRACH FFT点数、有效周期重复数；正整数 |
| beta、T | 有限非负幅度因子、resource.waveform_samples总采样点数 |

完整数组由前部零偏移、CP+有效周期、尾部guard组成。CP可能长于N，取模索引正确重复尾部；不把CP错误地限于useful[-CP:]。所有复幅度是平台归一化数值，不是瓦特或dBm；默认幅度与真实MATLAB导出一致。cell.n_tx_antennas不会自动复制本单端口波形，物理天线映射由外部明确提供。

| 输出dict键 | 说明、单位、维度 |
|---|---|
| waveform | complex[1,T]时域波形，已乘beta；采样率来自resource.cell |
| sequence | complex[L]单位模移位ZC，未乘beta |
| symbols | complex[L]未归一化DFT，未乘beta，幅度sqrt(L) |
| logical_root、root_sequence、cyclic_shift | 实际逻辑根0..L-2、物理根1..L-1、移位0..L-1；整数 |
| cp_samples、n_fft | 实际CP采样点数、PRACH FFT点数，正整数 |

阶段`tx.zc`、`tx.dft`、`tx.frequency_grid`、`tx.ifft`、`tx.waveform`记录真实中间结果；frequency_grid为complex[1,1,N]的独立PRACH频谱，不是普通NRGrid。stage图仅显示，不保存；禁用时不导入Matplotlib。独立调用结束非阻塞show，共享plotter由调用者show。

```python
from cell import NRCell
from prach import NRPRACH, NRPRACHTransmitter
r = NRPRACH(NRCell(),guard_samples=32)
sent = NRPRACHTransmitter(r).transmit(preamble_index=7,beta=1)
assert sent['waveform'].shape == (1,r.waveform_samples)
```

不承担RO许可、RAR/Msg3、功率控制、载频上变频或射频多天线波束赋形。时域CFO/样点TA/SNR噪声由NRChannel施加；PRACH不套用普通NROFDM的符号相位补偿。
