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
| w | 最终单端口捕获波形，供时域信道输入；取值范围/约束：有限复数，含beta及前后静默；单位：归一化复幅度；维度/类型：complex[1,T] |
| z | 一个有效PRACH周期，用于重复及循环前缀复制；取值范围/约束：有限复数，未乘beta；单位：归一化复幅度；维度/类型：complex[N] |
| s | CP首点在捕获数组内的位置；取值范围/约束：s=occasion_start_samples≥0；单位：采样点索引；维度/类型：整数标量 |
| i | 当前活动段内采样索引，用于循环取周期点；取值范围/约束：0..C_CP+RN−1；单位：采样点索引；维度/类型：整数标量 |
| C_CP | 循环前缀长度，决定复制多少个周期尾点；取值范围/约束：正整数，可能大于N；单位：采样点；维度/类型：整数标量 |
| N | 单个有效周期采样数，用于取模；取值范围/约束：N=Fs/Delta_f_RA>0；单位：采样点；维度/类型：整数标量 |
| R | 重复周期数，决定重复次数；取值范围/约束：1/2/4/6/12；单位：次数；维度/类型：整数标量 |
| beta | 发送线性幅度因子，缩放活动波形；取值范围/约束：有限实数≥0；单位：线性幅度；维度/类型：实标量 |
| T | 整个捕获数组长度，决定输出维度；取值范围/约束：T=s+C_CP+RN+guard_samples，正整数；单位：采样点；维度/类型：整数标量 |

完整数组由前部零偏移、CP+有效周期、尾部guard组成。CP可能长于N，取模索引正确重复尾部；不把CP错误地限于useful[-CP:]。所有复幅度是平台归一化数值，不是瓦特或dBm；默认幅度与真实MATLAB导出一致。cell.n_tx_antennas不会自动复制本单端口波形，物理天线映射由外部明确提供。

| 输出dict键 | 说明、单位、维度 |
|---|---|
| waveform | complex[1,T]时域波形，已乘beta；采样率来自resource.cell |
| sequence | complex[L]单位模移位ZC，未乘beta |
| symbols | complex[L]未归一化DFT，未乘beta，幅度sqrt(L) |
| logical_root | 本前导实际逻辑根号，定位物理根原表；范围：0..L−2；单位：根索引；维度：整数标量 |
| root_sequence | 物理ZC根u，进入二次相位公式；范围：1..L−1，由逻辑根查表获得；单位：根ID；维度：整数标量 |
| cyclic_shift | 循环提前点数C，生成当前前导；范围：0..L−1，按前导号与NCS导出；单位：ZC序列点；维度：整数标量 |
| cp_samples | 实际使用的前缀长度，定位有效段；范围：正整数，包含适用扩展；单位：采样点；维度：整数标量 |
| n_fft | 有效周期IFFT长度，决定每重复段长度；范围：Fs/Delta_f_RA，正整数；单位：采样点；维度：整数标量 |

阶段`tx.zc`、`tx.dft`、`tx.frequency_grid`、`tx.ifft`、`tx.waveform`记录真实中间结果；frequency_grid为complex[1,1,N]的独立PRACH频谱，不是普通NRGrid。stage图仅显示，不保存；禁用时不导入Matplotlib。独立调用结束非阻塞show，共享plotter由调用者show。

```python
from cell import NRCell
from prach import NRPRACH, NRPRACHTransmitter
r = NRPRACH(NRCell(),guard_samples=32)
sent = NRPRACHTransmitter(r).transmit(preamble_index=7,beta=1)
assert sent['waveform'].shape == (1,r.waveform_samples)
```

不承担RO许可、RAR/Msg3、功率控制、载频上变频或射频多天线波束赋形。时域CFO/样点TA/SNR噪声由NRChannel施加；PRACH不套用普通NROFDM的符号相位补偿。

## 从序列到时域数组：逐步对应

先阅读[资源文档的新手导读](NRPRACH.md#新手导读先从一次敲门理解-prach)。以下数值使用52 RB、UL30 kHz、A1/RA15 kHz、前导1、NCS=15、时域起点0、guard=32、beta=1。生成依据为TS38.211 V15.2.0 §6.3.3.1、§6.3.3.2、§5.3.2；数组形状和幅度归一化是本平台约定。

| 步骤 | 对应方法/语句 | 输入 → 输出 | 新手要注意的含义 |
|---|---|---|---|
| 1. 前导身份 | `resource.preamble_parameters(1)` | 标量1 → `(0,1,15)` | 逻辑根0、物理根1、循环移位15；三者不是同一个索引 |
| 2. ZC生成 | `resource.sequence(1)` | 根/移位 → complex[139] | 139个单位模复数，是生成序列，不是139个发送采样点 |
| 3. 序列DFT | `resource.generate(1)` | complex[139] → complex[139] | 139点FFT，未归一化；幅度约sqrt(139) |
| 4. 频谱映射 | `resource.spectrum(1)` | 139频率系数 → complex[2048] | 写到中心坐标bin −622～−484；FFT数组中使用取模索引；其余为零 |
| 5. PRACH IFFT | `resource.useful_waveform(1)` | complex[2048] → complex[2048] | 一周期66.666667 us，包含平台幅度归一化 |
| 6. 生成CP | `useful[arange(-CP,0) % N]` | 单周期 → complex[304] | 当前起点CP=304；从周期尾部循环取点 |
| 7. 重复并拼接 | `concatenate((prefix, tile(useful,2)))` | CP和周期 → complex[4400] | 仅开头有一次CP，不在第二个有效周期前再插CP |
| 8. 定位与缩放 | 写入`wave[0,start:start+active]` | 活动波形 → complex[1,4432] | 最后32点静默；实际waveform乘beta，返回sequence/symbols不乘beta |

第4步不是普通上行资源栅格映射：2048是独立PRACH FFT长度；本例普通NRCell OFDM FFT为1024。两个过程共享采样率，但频率间隔不同。

## 各阶段图应该看什么

| stage | 横轴/分支的含义 | 应该观察什么 |
|---|---|---|
| `tx.zc` | 139点序列索引；序列视图可展示实部/虚部等 | 复数模长为1、相位随根和移位改变；不能把横轴当时间采样 |
| `tx.dft` | 139个DFT系数索引 | 模长为sqrt(139)；数值较大来自DFT归一化约定，不是新增发射增益 |
| `tx.frequency_grid` | fftshift后的2048个PRACH频率bin；网格中只有一行 | 仅139点非零，检查相对载波中心的位置；该行不是普通UL时隙的某个符号 |
| `tx.ifft` | 2048个时域采样点 | 一有效周期，尚无CP、重复、偏移、guard或beta |
| `tx.waveform` | 完整输出采样点 | 活动段边界、前后静默；CP与有效周期的功率形状可能相似，不能只凭幅度曲线找CP边界 |

阶段图使用索引轴时，时间为采样索引除以Fs；频域图经fftshift后第j列的中心bin为`j-N//2`，频率为该bin乘RA间隔。精确起止位置应结合resource字段计算，不从图上的像素估计。

```python
from cell import NRCell
from prach import NRPRACH, NRPRACHTransmitter
from diagnostics import NRPlotConfig

cell = NRCell(n_size_grid=52, subcarrier_spacing_khz=30)
r = NRPRACH(cell, guard_samples=32)
tx = NRPRACHTransmitter(r, plot_config=NRPlotConfig(enabled=True, channel='PRACH'))
out = tx.transmit(preamble_index=1)
assert out['waveform'].shape == (1, 4432)
print('CP / useful / active:', r.cp_samples, r.n_fft, r.active_samples)

import matplotlib.pyplot as plt
plt.show()  # 显示阶段图；不保存文件
```

关闭绘图用`NRPlotConfig(enabled=False)`或保留`plot_config=None`。图中的序列、频谱和波形来自真实中间结果；多个UE共享plotter时会记录多次发送阶段，需结合调用顺序辨认UE。
