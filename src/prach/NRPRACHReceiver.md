# NRPRACHReceiver：前导检测及采样点时延

[源码](NRPRACHReceiver.py)。参考生成严格使用TS38.211 V15.2.0 §6.3.3.1/§6.3.3.2、§5.3.2；接收算法为本项目工程算法。接收真实[Rx,T]时域信号，在已知时机及可选已知CFO补偿后，按PRACH独立FFT进行相关，搜索前导及非负样点延迟。

| 字段 | 含义、范围、单位、示例 |
|---|---|
| resource | NRPRACH，包含所有公共时频参数与当前捕获长度，不包含待检出的前导号 |
| preamble_indices=tuple(range(64)) | 非空不重复tuple，每元素整数0..63；例(0,1,2)缩小搜索，不必把真实发送编号告诉接收机 |
| max_delay_samples=16 | 整数采样点D；0..min(CP,Nfft-1)，NCS非零时还须D<NCS*Nfft/L；例16；默认并非所有NCS/SCS均适用，需按时延预算设置 |
| detection_threshold=.2 | 有限实数0..1，相关归一化能量比严格大于门限才检测；不是dB或规范强制值 |
| plot_config=None | 可选NRPlotConfig，None关闭；例NRPlotConfig(enabled=True,channel='PRACH') |

构造/`__post_init__`校验所有字段。D不得跨相邻循环移位的等效时延间隔，避免把同一根的另一前导误当作传播延迟；此实现采用保守的公共窗口，即使候选前导列表稀疏也不自动放宽。NCS=0时每个前导使用不同根，不应用该移位间隔限制。

`receive(waveform,*,known_frequency_offset_hz=0,known_initial_phase_rad=0,plotter=None)`输入有限complex[Rx,T]，Rx严格等于cell.n_rx_antennas，T严格等于resource.waveform_samples。已知CFO单位Hz、初相单位rad，取负补偿；plotter为可选共享NRStagePlotter。接收机不接收真实信道、实际前导编号或真实时延，后两者均由相关估计。

## 接收公式与变量

下述PRACH-RX-1/2为文档自编号。算法使用上述固定R15生成参考；相关、合并及门限均为项目定义，不是3GPP接收机强制实现。

先按名义CP结束点取R段N点有效周期，跨重复相干平均，跨Rx非相干累加：

$$
v_r[n]=\frac1R\sum_{h=0}^{R-1}y_r[s+C_{CP}+hN+n],\qquad
c_{a,r}[d]=\operatorname{IFFT}_N\{\operatorname{FFT}_N(v_r)\operatorname{FFT}_N(z_a)^*\}[d].\tag{PRACH-RX-1}
$$

$$
E_y=\sum_{r,n}|v_r[n]|^2,\quad E_a=\sum_n|z_a[n]|^2,\quad
m_a[d]=\frac{\sum_r|c_{a,r}[d]|^2}{E_a E_y},\quad
\widehat d_a=\arg\max_{0\le d\le D}m_a[d],\quad
\widehat H_{a,r}=c_{a,r}[\widehat d_a]/E_a.\tag{PRACH-RX-2}
$$

| 变量 | 含义、范围、单位、维度 |
|---|---|
| a、r、h、n、d | 候选前导0..63、Rx索引0..Rx-1、重复索引0..R-1、周期内采样0..N-1、非负时延0..D；整数 |
| s、C_CP、N、R、D | 数组内CP起点、CP采样数、FFT点数、有效重复数、最大搜索样点；资源/接收配置正整数（s/D可0） |
| y、v、z_a | 输入complex[Rx,T]、周期平均complex[Rx,N]、候选参考complex[N]；归一化幅度 |
| c | 循环相关complex[候选,Rx,N]的概念值；实现逐候选计算，只保留窗口内功率，不存整个三维数组 |
| E_y、E_a | 非负接收能量和正参考能量，无绝对功率单位；按归一化幅度平方求和 |
| m、d_hat、H_hat | 归一化分数float[候选,D+1]、峰值样点整数、每Rx复增益complex[Rx] |

零能量时分数为0；数值计算后clip到[0,1]。每个候选独立满足m_peak>门限且接收能量>1e-20才报告。时延按sample/Fs得到秒，按sample*cell.tc_per_sample得到Tc数。这里报告**窗口内最强相关峰的相对传播延迟**，不是首次到达路径、绝对网络时间、距离或已量化的MAC TA命令。

多用户可以共享同一时频时机、同一根、不同循环移位；接收功率是所有用户之和，归一化分母也含所有用户和噪声。三个近似等功率且正交用户各自分数约1/3，不能期望每人都为1。弱用户可能被门限掩盖，threshold=.2不是通用虚警率或多用户容量保证。相同前导碰撞无法识别多个UE。

## 输出

| 字段 | 含义、单位与维度 |
|---|---|
| detected | 至少一个候选通过门限，bool |
| detections | 仅通过门限的候选dict列表；顺序同preamble_indices，不按分数重排 |
| candidates | 所有候选dict列表，包含失败者及其分数 |
| best_preamble_index | 最大峰分数的候选编号0..63；无人通过时None |
| delay_profiles | float[候选数,D+1]归一化分数，行严格对应preamble_indices |
| delay_axis_samples | int[D+1]，0..D采样点；不是12个循环移位窗或ZC索引 |

每个候选dict包含：preamble_index为整数编号；detected为bool；metric为0..1峰分数；delay_samples为非负整数样点；delay_seconds为秒；delay_tc为Tc数；channel_estimates为complex[Rx]归一化平坦复增益。未检出时后三种delay及channel_estimates均为None，metric仍返回诊断值。增益包含发送beta；多用户/多径泄漏会产生偏差，不能当作精确多径估计。

绘图阶段`rx.average`、`rx.frequency`、`rx.delay_profiles`、`rx.metrics`。默认只显示不保存，关闭不导入Matplotlib。profiles图分支顺序与候选列表一致；候选不连续时以结果的preamble_indices对应行，不将绘图行号当真实编号。

```python
import numpy as np
from cell import NRCell
from channel import NRChannel
from prach import NRPRACH, NRPRACHTransmitter, NRPRACHReceiver
cell = NRCell(n_rx_antennas=2)
r = NRPRACH(cell,guard_samples=32)
wave = NRPRACHTransmitter(r).transmit(7)['waveform']
wave = np.array([1,.7j])[:,None]*wave
wave = NRChannel(cell).timing_advance(wave,-7)  # 延迟7个采样点
out = NRPRACHReceiver(r).receive(wave)
assert out['best_preamble_index']==7
assert out['detections'][0]['delay_samples']==7
```

边界：已知RO、整数非负延迟、延迟不超过CP及移位间隔、跨重复信道/相位近似恒定。重复相干平均要求残余CFO足够小；当前只补偿给定CFO，没有盲CFO搜索。参考相同导致的碰撞、受限集合、高速多普勒、连续多RO扫描、分数采样插值、复杂多径首径识别、SIC和恒虚警自适应门限均未实现。原理和MATLAB验证边界见[验证报告](../../documentation/validation/NRPRACH_validation.md)。
