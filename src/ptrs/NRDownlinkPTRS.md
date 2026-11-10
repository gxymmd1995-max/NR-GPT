# NRDownlinkPTRS：CP-OFDM PT-RS资源和公共相位测量

固定TS38.211 **V15.2.0 §7.4.1.2、原表7.4.1.2.2-1**；Gold依据§5.2.1。源码[NRDownlinkPTRS.py](NRDownlinkPTRS.py)，共享R15实现位于[_core.py](_core.py)。配置关联[NRPDSCH](../pdsch/NRPDSCH.md)，只支持单层、连续RB、不跳频、CP-OFDM。上行变换预编码PT-RS未实现；多层/双PT-RS端口、DCI/MCS密度选择及自动预编码未实现。调用者已决定本次发送PT-RS。

## 新手导读：相位为什么需要参考

公共相位误差CPE会使一个OFDM符号内的QAM点整体转动。PT-RS在若干非DMRS符号、每2/4个RB插入一个已知复数点。已知有效信道后，将接收点乘信道及参考的共轭并合并，合并结果的相角就是本符号的CPE。此算法不消除子载波间干扰，也不等价于盲CFO估计。

```text
时域密度2：候选从分配起点开始；遇到DMRS后从最后DMRS+2重新计数
频域密度2：在分配中按RNTI确定首RB偏移，再每隔2个RB放一个参考点
DMRS参考 → 确定信道H → PT-RS观测 → angle → 对该符号所有子载波反旋转
```

不同time_density改变参考符号位置，frequency_density改变参考RB间距；re_offset按关联DMRS端口/类型查R15原表，不是任意指定子载波。参考序列来自**第一个DMRS符号**的Gold-QPSK，并取当前PT-RS子载波对应的基础序列位置；不是每个PT-RS符号重新初始化。

## 每个字段

| 字段 | 用途 | 范围/约束 | 单位 | 维度 |
|---|---|---|---|---|
| resource | 提供分配、RNTI、DMRS端口/序列与时序 | 必须NRPDSCH且n_layers=1，关联端口在原表内 | 资源对象 | 标量 |
| time_density=1 | PT-RS符号间隔，遇DMRS重置计数 | 1/2/4 | OFDM符号间隔 | 整数标量 |
| frequency_density=2 | 相邻PT-RS RB的间距 | 2/4 | RB间隔 | 整数标量 |
| re_offset=0 | 原表resourceElementOffset列 | 0..3分别表示00/01/10/11 | 列索引 | 整数标量 |

## 时频公式与变量

以下PT-1为本文自编号，依据固定§7.4.1.2的非变换预编码映射及原表7.4.1.2.2-1。

$$
 b_0=n_{RNTI}\bmod\begin{cases}K&N_{RB}\bmod K=0\N_{RB}\bmod K&\text{otherwise}\end{cases},\qquad
 k_{local}=12(b_0+iK)+k_{ref}.\tag{PT-1}
$$

| 变量 | 含义与用途 | 范围 | 单位 | 维度 |
|---|---|---|---|---|
| b0 | 分配内第一个PT-RS RB偏移 | 取模后的非负整数 | RB索引 | 整数标量 |
| n_RNTI | 调度RNTI，选择频域参考偏移 | 0..65535，来自resource.rnti | ID | 整数标量 |
| K | 频率密度间隔 | 2/4 | RB | 整数标量 |
| N_RB | 本次共享信道的RB数 | resource.n_prbs，正整数 | RB数 | 整数标量 |
| i | PT-RS频域点序号 | 从0递增，须b0+iK小于N_RB | 点索引 | 整数标量 |
| k_ref | 单RB内参考偏移，按关联端口/类型及re_offset查表 | 原表给出的0..11 | 子载波偏移 | 整数标量 |
| k_local | 本分配内的参考子载波，需再加BWP/PRB起点 | 0..12N_RB−1 | 子载波索引 | 整数标量 |

时间选择严格按该节重置步骤：从资源相对0开始，候选间隔内遇DMRS时把基准移到最后DMRS符号，然后再加time_density；双符号DMRS以第二符号为基准。因此不能只用“符号号mod time_density”筛选。

## 方法和接收算法

| 方法 | 输入、作用、输出 |
|---|---|
| __post_init__ | 检查方向类、单层、密度、RE偏移和关联端口；非法配置抛TypeError/ValueError |
| indices | int[RE,3]，列为本地端口0、slot符号、载波局部k；按时间后频率排序 |
| generate | complex[RE]单位模参考，不含beta，不执行数据加扰 |
| map_to_grid(grid,beta=1) | 写入同cell单端口NRGrid，beta有限非负线性幅度，返回点数；已有占用冲突时报错 |
| estimate_phase(rx_grid,channel_estimates) | 有限complex[Rx,L,K]网格及非零有限complex[Rx]平坦信道；返回下面字段 |

| 输出 | 含义 | 范围/单位 | 维度 |
|---|---|---|---|
| symbols | 实际PT-RS符号号，解释相位数组顺序 | 0..L−1，符号索引 | int[S] |
| phase_rad | 每参考符号跨Rx/频率合并的相角估计 | −π..π，rad | float[S] |
| corrected_grid | 在上述参考符号上按估计相角反旋后的新网格 | 归一化复幅度 | complex[Rx,L,K] |

接收算法为工程方案，非规范强制：合并量为sum(conj(H)×Y×conj(r))，相位取angle。H必须由外部DMRS估计等获得，不能把未知真实信道偷传为接收机估计；示例明确使用已知H=1来隔离相位验证。全零相关拒绝输出无依据相位。不同参考符号间不做时间插值/解缠绕，非PT-RS符号保留原值；频选信道应先在外部均衡。

## 与数据共存的当前边界

本资源可映射到空网格或已正确避让的网格，不覆盖共享信道数据。现有NRPDSCHTransmitter/Receiver尚未自动插入、排除PT-RS数据RE或自动调用相位补偿，因此**不能先发送完整数据，再用overwrite强行替换PT-RS**；那会造成编码位预算不匹配。本首版提供独立资源/序列/相位测量接口及参考专用时域演示，不宣称完成业务链路的PT-RS集成。

```python
from cell import NRCell
from pdsch import NRPDSCH
from ptrs import NRDownlinkPTRS
r = NRDownlinkPTRS(NRPDSCH(NRCell(n_size_grid=52)), time_density=2)
print(r.indices()[:3], r.generate()[:3])
```

[时域相位演示](../../examples/ptrs/NRDownlinkPTRS_demo.py)，[实际MATLAB验证](../../documentation/validation/NRReferenceSignals_validation.md)。图仅显示、不保存。
