# NRCSIRS：单端口CSI-RS资源、波形与平坦信道测量

固定TS38.211 **V15.2.0 §7.4.1.5.1～3、原表7.4.1.5.3-1的Row 1/2**。Gold依据§5.2.1，OFDM依据§5.3.1。源码[NRCSIRS.py](NRCSIRS.py)，导入`from csirs import NRCSIRS`。本类实现单端口3000、无CDM的NZP/ZP资源；没有实现Row 3～18多端口CDM、波束管理、CSI反馈码本、测量滤波或完整周期调度。调用者已选定本slot发送许可；不会根据TDD元数据自动判断下行。

## 新手导读：从序列到位置

CSI-RS是已知探测参考，不传输业务比特。每个有效OFDM符号先以slot号、符号号和scrambling_id初始化Gold，再两比特一组转单位模QPSK，按CRB位置选序列点，映射到NRGrid。通过NROFDM形成完整slot波形，再经过信道并OFDM解调。

```text
Row1：每RB三个参考点，例subcarrier=0
RB内偏移    0 1 2 3 4 5 6 7 8 9 10 11
             R . . . R . . . R . .  .
Row2：每RB一个参考点，密度0.5时只选奇/偶CRB
             R . . . . . . . . . .  .
```

点号表示本CSI-RS未使用，不表示其他信号静默。start_rb使用**公共CRB坐标**，不是BWP局部RB。半密度奇偶也按绝对CRB判断；即使分配不从CRB0开始，Gold寻址不重新从0开始。符号由symbol显式指定；row改变频率密度，不自动改变时间。30kHz每RB宽360kHz；单端口Row1在每RB取3个点，Row2取1个点或隔RB取1点。

## 构造字段：每个变量单独解释

| 字段 | 用途 | 范围/约束 | 单位 | 维度 |
|---|---|---|---|---|
| cell | 提供载波边界、FFT、slot及天线数 | NRCell实例 | 配置对象 | 标量 |
| row=2 | 选择R15位置表行 | 只接受1/2 | 行号 | 整数标量 |
| start_rb=0 | 资源首CRB | ≥cell.n_start_grid，完整分配须位于载波 | CRB索引 | 整数标量 |
| n_rbs=24 | 频率分配宽度 | 正整数且start_rb+n_rbs≤grid_start+grid_size | RB | 整数标量 |
| symbol=4 | slot内参考符号 | 2..min(12,slot符号数−1) | 符号索引 | 整数标量 |
| subcarrier=0 | RB内频率基准k0 | Row1为0..3，Row2为0..11 | 子载波索引 | 整数标量 |
| density=1 | 频率密度 | Row1只能3，Row2只能1/0.5 | RE/RB/端口 | 实标量 |
| rb_parity=0 | 半密度时选绝对CRB奇偶 | 0偶数、1奇数；其他密度时不影响 | 无量纲 | 整数标量 |
| scrambling_id=0 | Gold初始化ID | 0..1023，不自动等于PCI | ID | 整数标量 |
| zero_power=False | 生成ZP资源而不发送参考能量 | 严格bool；True时generate全0且不能估计信道 | 开关 | bool |

## 生成公式及变量

以下CSI-1为**本文自编号**，根据上述固定§7.4.1.5.2/3推导，限定Row1/2单端口、k_prime=0。

$$
 c_{init}=[2^{10}(L n_{slot}+l+1)(2N_{ID}+1)+N_{ID}]\bmod2^{31},\quad
 m=\lfloor n\rho\rfloor+\lfloor k_0\rho/12\rfloor,\quad
 r(m)=((1-2c(2m))+j(1-2c(2m+1)))/\sqrt2.\tag{CSI-1}
$$

| 变量 | 含义与用途 | 范围 | 单位 | 维度 |
|---|---|---|---|---|
| c_init | Gold种子，选择参考比特流 | 0..2^31−1 | 无量纲 | 整数标量 |
| L | 当前slot符号总数，决定种子时间寻址 | normal14/extended12 | 符号数 | 整数标量 |
| n_slot | 帧内slot索引，决定本slot参考 | 0..slots_per_frame−1 | slot索引 | 整数标量 |
| l | 已配置参考符号 | symbol字段 | 符号索引 | 整数标量 |
| N_ID | 序列初始化ID | 0..1023 | ID | 整数标量 |
| n | 当前参考所在绝对CRB | start_rb..start_rb+n_rbs−1；半密度再筛奇偶 | CRB索引 | 整数标量 |
| rho | 单端口频率密度 | 3、1或0.5，与row匹配 | RE/RB | 实标量 |
| k0 | 当前RB内频率位置，Row1逐个取k0/k0+4/k0+8 | 0..11 | 子载波索引 | 整数标量 |
| m | 本参考使用的QPSK序列位置，不从分配起点重置 | 非负整数 | 序列索引 | 整数标量 |
| c | Gold比特流 | 每点0/1 | bit | 一维比特序列 |
| j | 虚数单位 | j²=−1 | 无量纲 | 复常量 |
| r | 单位模QPSK参考 | 实虚部各为±1/sqrt(2) | 归一化复幅度 | complex[参考点数] |

## 每个方法与接收算法

| 方法 | 输入和用途 | 输出 |
|---|---|---|
| __post_init__ | 检查类型、表行、密度、频率及符号边界 | 非法配置抛TypeError/ValueError |
| _points | 内部遍历CRB及RB内参考点 | 有序(n,k)列表 |
| indices | 输出载波局部位置，不修改对象 | int[RE,3]，每行[端口0,slot符号,载波k] |
| generate | 生成上述参考，ZP时全0 | complex[RE]，未乘beta |
| map_to_grid(grid,beta=1) | 要求同cell单端口NRGrid；beta为有限非负线性幅度；冲突报错，不覆盖 | 写入RE数量 |
| waveform(beta=1) | 映射后普通OFDM，无RF载频上变频 | complex[1,cell.samples_per_slot] |
| estimate(rx_grid) | 有限complex[Rx,L,K]，先提取参考、乘本地共轭并平均 | channel_estimates为complex[Rx]；rsrp_per_rx为float[Rx] |

估计器使用工程平坦LS：每Rx沿实际参考点平均Y×conj(r)。发送beta包含在估计增益中；rsrp_per_rx是观测功率均值，包含噪声且未去偏，不是标定后的dBm。没有声称输出RI/PMI/CQI、时延或逐子载波频选信道。ZP和半密度无实际点时拒绝估计；输入无同步补偿时应先由外部处理。

```python
from cell import NRCell
from csirs import NRCSIRS
from common import NROFDM
r = NRCSIRS(NRCell(n_size_grid=52, subcarrier_spacing_khz=30), row=1, density=3)
y = NROFDM(r.cell).demodulate(r.waveform())
print(r.estimate(y)['channel_estimates'])  # 理想单支路约为1+0j
```

[时域示例与绘图](../../examples/csirs/NRCSIRS_demo.py)、[100 MHz / 30 kHz示例](../../examples/csirs/NRCSIRS_100MHz_30kHz_demo.py)，[实际MATLAB验证](../../documentation/validation/NRReferenceSignals_validation.md)。生成器只占自身参考资源；与PDSCH共存时须先按位置排除对应数据RE，当前PDSCH类尚未自动执行该速率匹配。
