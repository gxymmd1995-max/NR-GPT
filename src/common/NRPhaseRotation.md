# NRPhaseRotation：NR逐符号与定时相位

公式使用的标量、数组、单位和运算符总约定见[公式变量阅读指南](../../documentation/formula_reference.md#conventions)。下列辅助变量表不替代规范参数表；式号沿用本文自编号，协议版本/章节见各式原说明。


[NRPhaseRotation.py](NRPhaseRotation.py)集中管理OFDM相关相位因子，使用 `from common import NRPhaseRotation`。包含逐OFDM符号载波补偿、提前FFT窗口恢复，以及定时偏移的频域分析因子。[NROFDM](NROFDM.md)调用本类；连续CFO放在 [channel](../channel/NRChannel.md)。这不替代各物理信号自身序列循环移位、星座旋转或PRACH算法。

固定 **TS38.211 V15.2.0 §5.3.1/§5.4**。PRACH在§5.4使用不同上变频表达式，不适用本类的逐符号补偿。以下P1–P3为项目文档自编号，不是协议原公式号。

## 字段和每个接口

冻结slots dataclass，无缓存、无额外常量/属性。

| 字段 | 作用、单位与示例（项目接口表） |
|---|---|
| cell | 必填NRCell，用当前slot在子帧中的符号起点与CP；`NRPhaseRotation(NRCell(n_slot=1))` |
| carrier_frequency_hz=0.0 | 有限非负实数f0，Hz；不是载波频偏；`NRPhaseRotation(cell,3500000123)` |

自动`__init__`调用`__post_init__()`检查cell类型与载频；bool拒绝，类型错误TypeError，范围错误ValueError。

| 方法 | 参数、结果、示例 |
|---|---|
| `symbol_phases()` | 无参；新float数组[L]，发送补偿角rad，未wrap；`phase.symbol_phases()[0]` |
| `symbol_phasors(inverse=False)` | inverse严格bool；False返回exp(jφ)，True返回共轭；新complex128[L]；`phase.symbol_phasors(True)`用于接收 |
| `apply_grid(grid,inverse=False)` | grid为有限[P,L,K]复数，按符号广播phasor并返回新数组，不改标签；维度/非有限报ValueError，inverse验证同上 |
| `timing_phasors(delay_samples)` | 有限实数，样点单位，正数表示波形延迟；返回complex128[K]；可取负数或分数，如1.25。仅理想傅里叶时移分析，不实现有限波形分数延迟滤波 |
| `fft_window_phasors(advance_samples)` | Python int 0..Nfft-1；FFT相对有效起点提前a样点的恢复因子[K]，调用timing_phasors(-a)；bool/float拒绝 |

内部useful_starts为每个符号相对**子帧首**的有效起点采样号，bins为`arange(K)-K//2`。返回数组均为新对象，修改不影响下次调用。

**P1，TS38.211 V15.2.0 §5.4：** 上变频表达式中的符号相位原点是有效符号起点：

$$
\phi_l=-2\pi f_0(t_{start,l}+N_{CP,l}T_c),\quad p_l=e^{j\phi_l}.\tag{P1}
$$

**变量说明（项目辅助表，范围以本式上下文为准）**

| 符号/代码变量 | 含义与作用 | 取值范围/约束 | 单位 | 维度/类型 |
|---|---|---|---|---|
| $\phi_l$、$p_l$ | 发送符号相位与单位模旋转因子 | 相位为有限实数；p模长1 | rad、无量纲 | 各[L] |
| $f_0$ | 配置载频，不是残余频偏 | 非负有限；0表示不旋转 | Hz | 实标量 |
| $t_{start,l}$ | 当前符号CP起点相对子帧首 | [0,1 ms)，不累计SFN | s | [L] |
| $N_{CP,l}$、$T_c$ | 协议CP的Tc数、NR基本时间单位 | CP>0；Tc=1/1966080000 | Tc数、s | 每符号整数/常量 |
| $l$ | 表达式中对应的符号；数组按当前slot排列 | 返回数组索引0..L-1，起始时间取子帧位置 | 符号索引 | 整数标量 |

子帧从t=0开始，因此跨子帧本类按该参考重置；n_frame不额外加入相位。同一symbol的CP和有效部分使用同一p_l。普通CP的长CP按子帧符号位置计算，不能对每个slot首符号一律取长CP。

**P2，依据§5.3.1傅里叶关系的项目离散推导：** 正延迟d样点对应：

$$
q_k(d)=e^{-j2\pi(k-K/2)d/N_{FFT}}.\tag{P2}
$$

**变量说明（项目辅助表，范围以本式上下文为准）**

| 符号/代码变量 | 含义与作用 | 取值范围/约束 | 单位 | 维度/类型 |
|---|---|---|---|---|
| $q_k(d)$ | 正延迟d产生的频域相位 | 单位模复数 | 无量纲 | [K] |
| $d$ | 理想波形延迟；正数表示延迟 | 任意有限实数，允许负数/分数；不是TA正号 | sample | 实标量 |
| $k$、$K$ | 载波局部频点与载波子载波数 | 0≤k<K；K=12*n_size_grid | 索引、计数 | 整数标量 |
| $N_{FFT}$ | OFDM FFT长度 | cell.n_fft | sample | 整数标量 |
| $a$ | P3中FFT窗提前量，用q(-a)补偿 | Python int 0..Nfft-1；真实OFDM需落CP内 | sample | 整数标量 |

它与用载波局部k直接写指数存在一个可吸收入信道的常相位；本类明确使用有符号FFT频率bin。接收机FIR文档另说明其系数相位原点。

**P3，项目提前窗口恢复：** 若FFT窗口提前a样点，补偿为q_k(-a)。不应把它与NR载频补偿或连续频偏混为一项。

```python
import numpy as np
from cell import NRCell
from common import NRPhaseRotation

cell = NRCell(n_size_grid=24)
phase = NRPhaseRotation(cell, carrier_frequency_hz=3500000123)
grid = np.ones((2,14,288), dtype=complex)
np.testing.assert_allclose(phase.apply_grid(phase.apply_grid(grid), inverse=True), grid)
np.testing.assert_allclose(phase.timing_phasors(3)*phase.fft_window_phasors(3), 1)
print(phase.symbol_phases())
```

真实MATLAB nrOFDMInfo的SymbolPhases、实际调制及解调向量覆盖本类，详见 [验证报告](../../documentation/validation/NROFDM_validation.md)。单元测试还验证子帧参考、逆旋转、分数定时因子与错误输入。


## NRPhaseRotation符号核对例

24 RB时K=288，局部k=144对应有符号bin0，任意d的定时相位均为1；k=145、d=3、Nfft512时相位角为-2*pi*3/512，约-0.036816 rad。FFT提前3点的恢复相位角则为+0.036816 rad。
