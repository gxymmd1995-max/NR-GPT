# NRSRS：Release 15 探测参考信号

公式使用的标量、数组、单位和运算符总约定见[公式变量阅读指南](../../documentation/formula_reference.md#conventions)。下列辅助变量表不替代规范参数表；式号沿用本文自编号，协议版本/章节见各式原说明。


`NRSRS` 使用 [NRCell](../cell/NRCell.md) 提供小区、帧内时隙、CP 和活动 BWP，产生真正的 SRS 复数序列及 RE 坐标，再映射到 [NRGrid](../grid/NRGrid.md)。源码为 [NRSRS.py](NRSRS.py)，导入方式 `from srs import NRSRS`。

本类保留发送参考生成职责；已新增独立接收类 [NRSRSReceiver](NRSRSReceiver.md)，负责已OFDM解调采样的联合信道估计、宽/窄带噪声、每用户时延及上行RI/TPMI。

固定基线为 **TS 38.211 V15.2.0 §5.2、§6.4.1.4**，RRC 参数范围为 **TS 38.331 V15.2.1 §6.3.2 SRS-Config / SRS-Resource / SRS-PeriodicityAndOffset**。SRS 是上行参考信号，不携带用户数据。其协议端口为 1000+i，网格轴为本地 i；端口数不从物理收发天线数推断。

实现 1/2/4 端口，1/2/4 连续符号，comb 2/4，64 行全部带宽表、4 个带宽层级，组跳变/序列跳变、频率跳频与重复、周期/半持续/非周期资源的当前时隙合成。没有实现 OFDM 波形、信道传播/估计、闭环功控、DCI/MAC 解码、波束关系、资源集冲突优先级或 UE 射频能力检查。允许的 numerology 来自 NRCell；算法测试中的 numerology 不宣称适用于所有射频频段/设备。

`enabled` 是调用者给出的当前时隙许可。调用者须先处理非周期触发、半持续激活及 TDD 上行/灵活符号许可；默认 True 表示这些前提在本次仿真中已满足。NRCell.duplex_mode 目前仅是元数据，不能据此自动判断是否允许发送。`is_candidate_slot` 只代表周期条件，`is_active` 再与 enabled 相与。非周期资源没有内置未来触发队列。

## 可运行入口

在仓库根目录安装 `pip install -e ".[dev,plots]"` 后运行：

```python
from cell import NRCell
from grid import NRGrid
from srs import NRSRS

cell = NRCell(n_cell_id=42, n_size_grid=52, n_start_grid=10,
              bwp_start=20, bwp_size=24, n_tx_antennas=4, n_rx_antennas=2)
srs = NRSRS(cell, n_ports=4, n_symbols=4, start_position=5,
            c_srs=7, b_srs=1, b_hop=0, k_tc=4, comb_offset=1,
            cyclic_shift=7, frequency_shift=10, sequence_id=42,
            group_seq_hopping="groupHopping")
grid = NRGrid(cell, n_ports=srs.n_ports)
raw = srs.generate()                    # (144,4)，未施加端口功率缩放
indices = srs.indices()                 # (576,3)，[本地端口,符号,载波内子载波]
assert srs.map_to_grid(grid) == 576      # 每 RE 写入 raw/sqrt(4)
assert grid.occupied_re_count == 576
print(srs.sequence_parameters())         # 每符号 u/v、每端口 alpha
```

完整示例：[NRSRS_demo.py](../../examples/srs/NRSRS_demo.py)。所有数值、CSV、日志和图片输出到 `examples/srs/`，详见 [示例说明](../../examples/srs/README.md)。

![四端口 SRS 网格与梳齿](../../examples/srs/NRSRS_allocation.png)

图中棕色为统一色表的 SRS `#8C564B`；上排为实际 NRGrid 占用，虚线是 BWP，下面是首个 SRS 符号两 RB 的梳齿细节。示例 cyclic_shift=7、comb4、四端口时，端口 1/3 的频域梳齿偏移与端口 0/2 不同。

## 输入字段：19 个

实例为 frozen、slots dataclass。修改使用 `dataclasses.replace`，返回新对象；推进小区时隙后也应重建对应 NRGrid。全部整数要求 Python int，拒绝 bool、float、NumPy int；字符串须使用表中准确拼写。以下是项目 API 对照表，**不是规范原表**；规范依据在最后一列。

| 字段 / 默认值 | 作用、单位与范围 | 独立可运行示例（已导入上述三个类） | 原文定位 |
|---|---|---|---|
| `cell`，必填 | NRCell，不可变小区对象 | `NRSRS(NRCell(n_cell_id=42))` | 38.211 V15.2.0 §4、§6.4.1.4 |
| `n_ports=1` | SRS 逻辑端口数 1/2/4 | `NRSRS(NRCell(), n_ports=2)` | 同版本 §6.4.1.4.1；38.331 V15.2.1 §6.3.2 nrofSRS-Ports |
| `n_symbols=1` | 连续 OFDM 符号数 1/2/4 | `NRSRS(NRCell(), n_symbols=4, start_position=3)` | 38.211 同节；38.331 同节 resourceMapping |
| `start_position=0` | 从时隙末尾反向计数的 l_offset，0..5；至少 n_symbols-1 | `NRSRS(NRCell(), start_position=5).symbol_start` → 8 | 38.211 V15.2.0 §6.4.1.4.1 |
| `c_srs=0` | 带宽配置表行号 0..63 | `NRSRS(NRCell(), c_srs=7).bandwidth_rb` → 24 | 38.211 V15.2.0 §6.4.1.4.3，表 6.4.1.4.3-1 |
| `b_srs=0` | 带宽层级 0..3 | `NRSRS(NRCell(), c_srs=7, b_srs=1).bandwidth_rb` → 12 | 同表，b-SRS |
| `b_hop=0` | 0..3；b_hop < b_srs 开启频率跳频 | `NRSRS(NRCell(), c_srs=7, b_srs=1, b_hop=0)` | 38.211 同节频率位置公式 |
| `k_tc=2` | comb 间隔，单位子载波，只接受 2/4 | `NRSRS(NRCell(), k_tc=4).sequence_length` → 12 | §6.4.1.4.2/3；38.331 transmissionComb |
| `comb_offset=0` | comb 内子载波偏移 0..k_tc-1 | `NRSRS(NRCell(), k_tc=4, comb_offset=3).indices()[0,2]` → 3 | §6.4.1.4.3 k_TC |
| `cyclic_shift=0` | comb2:0..7，comb4:0..11；循环移位编号，不是 rad | `NRSRS(NRCell(), k_tc=4, cyclic_shift=11)` | §6.4.1.4.2；38.331 cyclicShift-n2/n4 |
| `frequency_shift=0` | 本 API 的载波内起始 RB 偏移，0..268，映射 MATLAB FrequencyStart | `NRSRS(NRCell(), frequency_shift=4).indices()[0,2]` → 48 | §6.4.1.4.3 n_shift；38.331 freqDomainShift 范围 |
| `frequency_position=0` | n_RRC，0..67，频域循环位置参数，基本步长 4RB | `NRSRS(NRCell(), c_srs=7, b_srs=1, b_hop=3, frequency_position=3)` | §6.4.1.4.3 n_b；38.331 freqDomainPosition |
| `sequence_id=0` | 独立序列标识 0..1023；**不默认等于 PCI** | `NRSRS(NRCell(n_cell_id=42), sequence_id=19)` | §6.4.1.4.2；38.331 sequenceId 是 10 bit |
| `group_seq_hopping="neither"` | `neither` / `groupHopping` / `sequenceHopping`，互斥 | `NRSRS(NRCell(), c_srs=6, group_seq_hopping="sequenceHopping")` | §6.4.1.4.2，使用 §5.2.1 PRBS |
| `repetition=1` | 1/2/4，且不大于 n_symbols；同一频率位置连续使用 R 个符号，不强制序列 u/v 相同 | `NRSRS(NRCell(), n_symbols=4, start_position=3, repetition=2)` | §6.4.1.4.3 n_SRS；38.331 repetitionFactor |
| `resource_type="periodic"` | `periodic` / `semi-persistent` / `aperiodic` | `NRSRS(NRCell(), resource_type="aperiodic", enabled=True)` | §6.4.1.4.3/4；38.331 resourceType |
| `periodicity=1` | 时隙，固定集合见 PERIODICITIES；非周期必须为 1 | `NRSRS(NRCell(n_slot=3), periodicity=10, slot_offset=3).is_active` → True | §6.4.1.4.4；38.331 SRS-PeriodicityAndOffset |
| `slot_offset=0` | 周期内时隙偏移 0..periodicity-1；非周期必须为 0 | `NRSRS(NRCell(n_slot=2), periodicity=4, slot_offset=1).is_active` → False | 同上 |
| `enabled=True` | 外部提供的触发/激活/上行许可，严格 bool | `NRSRS(NRCell(), enabled=False).generate().shape` → (0,1) | 软件接口；许可边界依据 §6.4.1.4.4 与 38.213 V15.3.0 §11.1 |

`frequency_shift` 使用载波局部坐标，与 MATLAB FrequencyStart 一致。若希望从 BWP 的 PRB 0 开始，传入 `cell.bwp_start-cell.n_start_grid`。若希望从 BWP 内 PRB q 开始，再加 q。它不自动从 BWP 起点加一次偏移，也不直接接收整个 ASN.1 RRC 对象。所有实际 RE 均需在活动 BWP 内；`indices/generate/map_to_grid` 会报错，禁止裁剪/折返。非候选或 disabled 时不分配 RE，不进行当前分配范围检查。

## 常量和派生属性

以下为项目接口/推导表，规范出处见后续公式。

| 名称 | 含义 / 示例 |
|---|---|
| `SPEC_BASELINE` | 两份固定规范版本字符串；`print(srs.SPEC_BASELINE)` |
| `PERIODICITIES` | R15 的 17 种时隙周期：1,2,4,5,8,10,16,20,32,40,64,80,160,320,640,1280,2560；不含后续版本的 128/256/512 等新增项 |
| `symbol_start` | 时隙内 l0；普通 CP start_position=5 得 8；扩展 CP 得 6 |
| `bandwidth_rb` | m_b，单位 RB；C=7/B=1 得 12 |
| `sequence_length` | M，每端口每 OFDM 符号复数个数；C=7/B=1/comb4 得 36 |
| `max_cyclic_shifts` | comb2 为 8、comb4 为 12 |
| `antenna_ports` | 协议端口元组；四端口得 (1000,1001,1002,1003) |
| `absolute_slot` | SFN 周期内 n_frame*slots_per_frame+n_slot；30kHz 的 frame=1/slot=3 得 23 |
| `is_candidate_slot` | 仅周期条件；非周期始终 True，因为实际目标时隙由调用者确定 |
| `is_active` | enabled 且候选时隙；半持续资源只有调用者传入 enabled=True 才视为已激活 |

没有隐藏的可变缓存、随机种子或 logger 成员。`_tables.py` 中的 `PHI_12`、`PHI_24`、`BANDWIDTH_TABLE` 是不可变元组，索引分别为 `[u][n]` 和 `[c_srs][2*b:2*b+2]`。数值逐项对照英文 PDF；不从 MATLAB 输出生成 Python 表。

## 方法、参数、返回和失败行为

| 方法 | 输入 / 返回 / 行为 |
|---|---|
| 自动 `__init__(cell, ...)` | 使用上述全部字段构建冻结配置，随后调用 __post_init__；例如 `NRSRS(NRCell())` |
| `__post_init__()` | 类型、R15 范围、时间位置/重复/周期联合校验；TypeError 表示类型错误，ValueError 表示范围/组合错误；频域实际分配边界延迟到生成时检查 |
| `_frequency_indices()` | 内部无参，返回新数组 `(nb,k0)`，尺寸分别 `(b_srs+1,n_symbols)`、`(n_ports,n_symbols)`，整数；计算频率位置/跳频，不应用 enabled，也不承诺非候选时隙的 n_b 有协议发送含义；仅供验证诊断 |
| `indices()` | 无参，N×3 int64，从零起始 `[port,symbol,subcarrier]`，顺序为端口→SRS符号→序列点；不活跃返回 `(0,3)`；BWP 越界 ValueError。例如 `srs.indices()[:3]` |
| `sequence_parameters()` | 无参，返回 `{"u":(L,), "v":(L,), "alpha":(P,)}` 新数组；alpha 单位 rad；不应用时隙许可，方便配置诊断。例如 `srs.sequence_parameters()["alpha"]` |
| `generate()` | 无参，complex128，形状 `(M*L,P)`，每列一个端口，每符号内频率点递增；原始单位模序列，不含 beta 和 1/√P；不活跃返回 `(0,P)`；先验证实际 BWP 边界 |
| `map_to_grid(grid,beta=1.0,owner="SRS",overwrite=False)` | grid 必须为 NRGrid，同值 NRCell，且端口数≥P；使用前 P 个局部端口。beta 为非负有限 Python int/float 线性幅度，拒绝 bool/NaN/Inf/复数；owner/overwrite 约束继承 NRGrid。返回写入 RE 数；不活跃返回 0。写入 beta/√P*generate().ravel(order="F")；冲突或错误不产生部分写入 |
| `to_dict()` | 全部 19 个输入字段的新字典，cell 为独立 dict，可 JSON 编码。例如 `json.dumps(srs.to_dict())`；无需传入参数 |
| `to_matlab_config()` | nrSRSConfig 字段 dict；禁用全部相关后续扩展，enabled=False 导出 SRSPeriod="off"，非周期启用时为 "on"，周期/半持续为 [T,offset]；carrier 从 cell.to_matlab_config 单独构造。NFrame 与帧内 NSlot 成对输入，不能再把 NSlot 改为 absolute_slot，否则 MATLAB 重复累计帧号 |

`indices()` 与 `generate()` 返回值相互对应：`values=generate().ravel(order="F")`。NRGrid 数组轴是 `[p,l,k]`，MATLAB 下标是 `[k,l,p]`；MATLAB `nrSRSIndices(...,'IndexBase','0based','IndexStyle','subscript')` 列重排 `[3,2,1]` 后与 indices 一致。失败采用 NRGrid 的预检查和原子写入；不会自动覆盖同 owner。

```python
from dataclasses import replace

next_cell = cell.with_slot_offset(1)
next_srs = replace(srs, cell=next_cell, repetition=4)
next_grid = NRGrid(next_cell, next_srs.n_ports)
next_srs.map_to_grid(next_grid, beta=0.5, owner="SRS:UE0")
off = replace(next_srs, enabled=False)
assert off.indices().shape == (0, 3)
```

Gold序列和SRS的u/v获取已移至公共类 [NRCommon](../common/NRCommon.md)：`NRCommon.gold_sequence(c_init,length,offset=0)` 实现 §5.2.1；`NRCommon.srs_sequence_uv(...)` 实现 §6.4.1.4.2。NRSRS.sequence_parameters 委托公共类取得u/v，端口alpha仍在本类计算。模块内仅保留 `_integer(name,value,lower,upper)` 的本类参数校验，以及 `_base_sequence(length,u,v)` 的SRS所需12/24或≥36点基序列实现。

## 表格与公式追溯

以下 S1–S11 均为**本文档自编号，不是 3GPP 原公式号**。本节除 RRC 范围表外统一采用 **TS 38.211 V15.2.0**。

| 内容 | 原文章节 / 原表 | 代码数据 |
|---|---|---|
| 12 点 φ(n)，30 组 | §5.2.2.2，表 5.2.2.2-2 | `_tables.py: PHI_12` |
| 24 点 φ(n)，30 组 | §5.2.2.2，表 5.2.2.2-4 | `_tables.py: PHI_24` |
| 64 行×4 层级的 m_b/N_b | §6.4.1.4.3，表 6.4.1.4.3-1 | `_tables.py: BANDWIDTH_TABLE` |
| 端口、时域符号/起点 | §6.4.1.4.1，无独立表号 | n_ports/n_symbols/start_position |
| 周期、10 bit ID、位置范围 | TS 38.331 V15.2.1 §6.3.2 SRS-Config ASN.1，无独立表号 | PERIODICITIES 与字段校验 |

下表摘录自 **TS 38.211 V15.2.0 §6.4.1.4.3，原表 6.4.1.4.3-1**，不是重新设计的带宽表；完整 64 行见 [_tables.py](_tables.py)。

| C_SRS | m0,N0 | m1,N1 | m2,N2 | m3,N3 |
|---|---|---|---|---|
| 0 | 4,1 | 4,1 | 4,1 | 4,1 |
| 3 | 16,1 | 4,4 | 4,1 | 4,1 |
| 7 | 24,1 | 12,2 | 4,3 | 4,1 |
| 17 | 64,1 | 32,2 | 16,2 | 4,4 |
| 63 | 272,1 | 16,17 | 8,2 | 4,2 |

**S1，§6.4.1.4.1/3：时间起点和序列长度。**

$$
l_0=N_{symb}^{slot}-1-l_{offset},\qquad M=m_{SRS,b}\,12/K_{TC}.
$$

**变量说明（项目辅助表，范围以本式上下文为准）**

| 符号/代码变量 | 含义与作用 | 取值范围/约束 | 单位 | 维度/类型 |
|---|---|---|---|---|
| $l_0$、$l_{offset}$ | SRS起始slot符号号、从slot尾反向计数的start_position | 0≤l0<L；offset=0..5且≥n_symbols-1 | 符号索引、符号计数 | 各一整数标量 |
| $N_{symb}^{slot}$ | L，slot符号数 | normal14/extended12 | 符号计数 | 整数标量 |
| $M$、$m_{SRS,b}$ | 每端口每符号序列点数、该带宽层的RB数 | M=12*m/Ktc；m来自原表6.4.1.4.3-1 | 序列点、RB | 各一整数标量 |
| $K_{TC}$ | comb间隔 | 2或4；相邻序列点隔Ktc个网格子载波 | 子载波/序列点 | 整数标量 |

**S2，§6.4.1.4.2：端口循环移位。** 令 P=n_ports，i=p_i-1000。

$$
n_{cs,i}=(n_{cs}+n_{cs,max}i/P)\bmod n_{cs,max},\quad
\alpha_i=2\pi n_{cs,i}/n_{cs,max},\quad n_{cs,max}=8\;(K=2),12\;(K=4).
$$

**变量说明（项目辅助表，范围以本式上下文为准）**

| 符号/代码变量 | 含义与作用 | 取值范围/约束 | 单位 | 维度/类型 |
|---|---|---|---|---|
| $P,i,p_i$ | SRS端口数、局部端口号、协议端口号 | P=1/2/4；0≤i<P；p_i=1000+i | 端口计数、索引、标识 | 各一整数标量 |
| $n_{cs}$、$n_{cs,i}$ | 配置循环移位号、端口派生循环移位号 | 整数0..n_cs_max-1 | 无量纲移位号 | 标量、[P] |
| $n_{cs,max}$ | 循环移位号个数 | comb2为8；comb4为12 | 计数 | 整数常量 |
| $\alpha_i$ | 序列逐点相位增量 | 2*pi*n_cs_i/n_cs_max，0≤alpha<2*pi | rad/序列点 | [P] |
| $K$ | 此式括号中的comb简写，等于K_TC | 2/4；不是网格子载波数K | 子载波间距 | 整数标量 |

**S3，§5.2.2、§5.2.2.1/2：基序列及循环移位。** M=12/24 时取对应原表 φ。M≥36 时 N_ZC 为严格小于 M 的最大质数：

$$
r_i(n,l')=e^{j\alpha_i n}\bar r_{u,v}(n),\quad
\bar r_{u,v}(n)=
\begin{cases}e^{j\varphi_u(n)\pi/4},&M=12,24\\
e^{-j\pi q m(m+1)/N_{ZC}},\ m=n\bmod N_{ZC},&M\ge36
\end{cases}
$$

**变量说明（项目辅助表，范围以本式上下文为准）**

| 符号/代码变量 | 含义与作用 | 取值范围/约束 | 单位 | 维度/类型 |
|---|---|---|---|---|
| $r_i(n,l')$、$\bar r_{u,v}(n)$ | 端口循环移位后序列与基序列 | 复数模长1；生成时未乘beta/sqrt(P) | 归一化复幅度 | 每端口/符号[M]；接口[M*n_symbols,P] |
| $n,l'$、$i$ | 序列点、SRS内符号、端口索引 | 0≤n<M；0≤l_prime<n_symbols；0≤i<P | 索引 | 整数标量 |
| $u,v$ | 组号和组内序列编号 | u=0..29；v=0/1 | 无量纲ID | 每SRS符号标量 |
| $\varphi_u(n)$ | 短序列相位表整数 | 原表中的-3/-1/1/3 | pi/4相位系数 | [M]整数数组 |
| $M,N_{ZC},m$ | 序列长度、ZC质数长度、模ZC索引 | 本类M=12/24或≥36；Nzc为严格小于M最大质数；0≤m<Nzc | 点数、点数、索引 | 整数标量 |
| $q,\alpha_i$ | ZC根参数与循环移位相位步长 | q由下式得到，非零根；alpha见S2 | 无量纲、rad/点 | 整数/实标量 |

$$
\bar q=N_{ZC}(u+1)/31,\quad q=\lfloor\bar q+1/2\rfloor+v(-1)^{\lfloor2\bar q\rfloor}.
$$

**变量说明（项目辅助表，范围以本式上下文为准）**

| 符号/代码变量 | 含义与作用 | 取值范围/约束 | 单位 | 维度/类型 |
|---|---|---|---|---|
| $\bar q,q$ | 用于选择根的中间实数与最终整数根 | qbar=Nzc*(u+1)/31；q按取整式得出 | 无量纲 | 实标量、整数标量 |
| $N_{ZC}$ | 严格小于M的最大质数 | M≥36时使用；例如M=144时为139 | 序列点数 | 正整数标量 |
| $u,v$ | 基序列组号/组内编号 | u=0..29；v=0/1；SRS仅M≥72且开启sequenceHopping时v可变化 | ID | 整数标量 |

SRS 的原表 m_b 都是 4 的倍数，所以本类不产生 6/18/30 点序列。实现先对整数 ZC 相位模 2π，再取指数；与原式代数等价，但与 MATLAB 直接计算大相位存在可测的浮点舍入差。

**S4，§5.2.1：Gold PRBS。** x1(0)=1，其余前31位为0；x2 的前31位按 c_init=sequence_id 的低位先装载；Nc=1600。

$$
x_1(n+31)=x_1(n+3)\oplus x_1(n),\quad
x_2(n+31)=x_2(n+3)\oplus x_2(n+2)\oplus x_2(n+1)\oplus x_2(n),
\quad c(n)=x_1(n+1600)\oplus x_2(n+1600).
$$

**变量说明（项目辅助表，范围以本式上下文为准）**

| 符号/代码变量 | 含义与作用 | 取值范围/约束 | 单位 | 维度/类型 |
|---|---|---|---|---|
| $x_1,x_2,c$ | 两个31级寄存器序列与输出Gold序列 | 每点0/1 | bit | 一维uint8序列 |
| $n,N_c$ | 输出比特号与固定跳过长度 | n≥0；Nc=1600 | bit索引、bit数 | 整数标量 |
| $c_{init}$ | 此SRS场景的sequence_id初始化种子 | 0..1023；通用Gold上限更大 | 无量纲ID | 整数标量 |
| $\oplus$ | 比特异或 | 等价加法模2 | 无量纲运算 | 逐bit |

**S5，§6.4.1.4.2：组/序列跳变。** 令 t=n_slot*N_symb_slot+l0+l'，此处使用帧内 slot；每帧重新以 sequence_id 初始化 PRBS。

$$
u=(f_{gh}+n_{ID}^{SRS})\bmod30,\quad
f_{gh}=\begin{cases}\sum_{m=0}^7 c(8t+m)2^m\bmod30,&groupHopping\\0,&其他\end{cases}
$$

**变量说明（项目辅助表，范围以本式上下文为准）**

| 符号/代码变量 | 含义与作用 | 取值范围/约束 | 单位 | 维度/类型 |
|---|---|---|---|---|
| $u,f_{gh}$ | 基序列组号与组跳变偏移 | 0..29 | 无量纲ID/偏移 | 每SRS符号整数标量 |
| $n_{ID}^{SRS}$ | sequence_id | 0..1023，不自动使用PCI | 无量纲ID | 整数标量 |
| $t$ | 帧内线性OFDM符号位置 | n_slot*L+l0+l_prime；0..slots_per_frame*L-1 | 符号索引 | 整数标量 |
| $m,c(8t+m)$ | 8个Gold比特位号与比特 | m=0..7；c为0/1 | bit索引、bit | 标量 |

$$
v=\begin{cases}c(t),&sequenceHopping\ 且\ M\ge72\\0,&其他\end{cases}.
$$

**变量说明（项目辅助表，范围以本式上下文为准）**

| 符号/代码变量 | 含义与作用 | 取值范围/约束 | 单位 | 维度/类型 |
|---|---|---|---|---|
| $v$ | 组内序列号 | 0/1，条件不满足则0 | 无量纲ID | 每SRS符号整数标量 |
| $M$ | 每端口每符号序列长度 | 正整数；≥72才允许序列跳变 | 序列点数 | 整数标量 |
| $c(t),t$ | 帧内符号t位置的Gold比特与索引 | bit=0/1；t同S5前式 | bit、符号索引 | 整数标量 |

**S6，§6.4.1.4.3/4：候选时隙和传输计数。** 令 a=n_frame*N_slots_frame+n_slot，T/Toffset 单位为 slot：

$$
(a-T_{offset})\bmod T=0,\quad
n_{SRS}=\begin{cases}\lfloor l'/R\rfloor,&aperiodic\\
((a-T_{offset})/T)(N_{symb}^{SRS}/R)+\lfloor l'/R\rfloor,&periodic/semi\text{-}persistent.
\end{cases}
$$

**变量说明（项目辅助表，范围以本式上下文为准）**

| 符号/代码变量 | 含义与作用 | 取值范围/约束 | 单位 | 维度/类型 |
|---|---|---|---|---|
| $a,n_{frame},n_{slot}$ | 本文a为帧展开slot号；SFN和帧内slot | a=SFN*slots_per_frame+n_slot；SFN0..1023 | slot、帧索引、slot索引 | 各一整数标量 |
| $T,T_{offset}$ | 周期与偏移，periodicity/slot_offset | T取R15 PERIODICITIES集合，1..2560；offset=0..T-1 | slot | 整数标量 |
| $n_{SRS}$ | 用于跳频的SRS传输计数 | 候选时隙中为非负整数；SFN回绕后按本cell重算 | 传输计数 | 每SRS符号整数 |
| $N_{symb}^{SRS},R,l'$ | SRS符号数、重复因子、SRS局部符号号 | 符号数1/2/4；R=1/2/4且整除符号数；0≤l_prime<Nsymb | 符号计数、符号/重复组、索引 | 整数标量 |

SFN 从1023回到0时使用回绕后的 NRCell 帧号；本类不额外保存无限递增帧计数。

**S7，§6.4.1.4.3：频率位置。** 无跳频或 b≤b_hop 时 n_b=⌊4n_RRC/m_b⌋ mod N_b。否则：

$$
n_b=(F_b(n_{SRS})+\lfloor4n_{RRC}/m_b\rfloor)\bmod N_b.
$$

**变量说明（项目辅助表，范围以本式上下文为准）**

| 符号/代码变量 | 含义与作用 | 取值范围/约束 | 单位 | 维度/类型 |
|---|---|---|---|---|
| $b,B_{SRS},b_{hop}$ | 带宽层号、配置层数终点、跳频起始层 | b=0..B_SRS；B_SRS/b_hop=0..3 | 带宽层索引 | 整数标量 |
| $n_b$ | 第b层频率位置索引 | 0..N_b-1 | 频率位置索引 | 每符号/层整数 |
| $n_{RRC}$ | frequency_position，RRC给定频率位置 | 0..67 | 无量纲频率配置 | 整数标量 |
| $m_b,N_b$ | 该带宽层RB宽度与分支位置数 | 由固定R15表6.4.1.4.3-1读取，均正整数 | RB、位置计数 | 每层一个整数 |
| $F_b,n_{SRS}$ | 跳频偏移与传输计数 | 整数；最后模N_b；nSRS≥0 | 无量纲、传输计数 | 整数标量 |

在 F_b 的乘积中强制 N_bhop=1。令 D=∏从 b_hop 到 b-1 的 N，z=(n_SRS mod(D*N_b))/D；以下 D/z 是为排版引入的本文符号：

$$
F_b=\begin{cases}(N_b/2)\lfloor z\rfloor+\lfloor z/2\rfloor,&N_b为偶数\\
\lfloor N_b/2\rfloor\lfloor n_{SRS}/D\rfloor,&N_b为奇数.\end{cases}
$$

**变量说明（项目辅助表，范围以本式上下文为准）**

| 符号/代码变量 | 含义与作用 | 取值范围/约束 | 单位 | 维度/类型 |
|---|---|---|---|---|
| $D$ | 跳频公式为排版引入的层间分支数乘积 | 乘积含b_hop..b-1；按本节N_bhop=1，故D≥1 | 无量纲 | 正整数标量 |
| $z$ | 传输计数在一周期内的归一化位置 | 0≤z<N_b，未取整前可为分数 | 无量纲 | 实标量 |
| $F_b,N_b$ | 第b层跳频偏移及该层分支数 | F_b整数；N_b来自原表；F_b最终参与mod N_b | 无量纲 | 整数标量 |
| $n_{SRS},b$ | SRS传输计数与带宽层号 | nSRS≥0；b> b_hop时使用此式 | 计数、层索引 | 整数标量 |

**S8，§6.4.1.4.3：每端口起点和特殊 comb 偏移。** 当 P=4、基础 n_cs≥n_cs,max/2 且 i=1/3 时，k_TC,i=(comb_offset+K_TC/2) mod K_TC；其他端口 k_TC,i=comb_offset。

$$
k_{0,i}(l')=12n_{shift}+k_{TC,i}+\sum_{b=0}^{B_{SRS}}K_{TC}M_b n_b(l').
$$

**变量说明（项目辅助表，范围以本式上下文为准）**

| 符号/代码变量 | 含义与作用 | 取值范围/约束 | 单位 | 维度/类型 |
|---|---|---|---|---|
| $k_{0,i}(l')$ | 端口i在SRS符号l_prime的起始载波局部子载波 | 0..K_grid-1且全部映射点须落BWP | 子载波索引 | [P,n_symbols] |
| $n_{shift}$ | frequency_shift；本平台相对载波起点RB偏移 | 0..268，另受BWP包含校验 | RB | 整数标量 |
| $k_{TC,i}$ | 端口派生comb偏移，含4端口特殊规则 | 0..K_TC-1 | 子载波偏移 | [P] |
| $K_{TC},M_b,n_b$ | comb间隔、该层序列长度、频率位置 | Ktc=2/4；Mb=12*m_b/Ktc；0≤nb<Nb | 子载波/点、点数、索引 | 整数标量/每层数组 |
| $i,l',b,B_{SRS}$ | 端口、SRS符号、累加层和层终点 | i<P；l_prime<n_symbols；b=0..B_SRS≤3 | 索引 | 整数标量 |

**S9，§6.4.1.4.3：RE 映射与幅度。**

$$
k=k_{0,i}+K_{TC}n,\quad l=l_0+l',\quad a_{k,l}^{(i)}=\beta_{SRS}r_i(n,l')/\sqrt{P}.
$$

**变量说明（项目辅助表，范围以本式上下文为准）**

| 符号/代码变量 | 含义与作用 | 取值范围/约束 | 单位 | 维度/类型 |
|---|---|---|---|---|
| $k,l$ | 映射到载波局部频率与slot符号坐标 | k∈活动BWP；l=0..L-1 | 子载波索引、符号索引 | 每RE两个整数 |
| $n,l',i$ | 序列点、SRS局部符号、逻辑端口 | 0≤n<M；l_prime<n_symbols；i<P | 索引 | 整数标量 |
| $k_{0,i},l_0,K_{TC}$ | 端口频率起点、slot时间起点、comb间隔 | 起点按S8/S1；Ktc=2/4 | 子载波、符号、子载波/点 | 标量或按端口/符号变化 |
| $\beta_{SRS},P$ | 发送线性幅度因子与端口数 | beta≥0有限；P=1/2/4 | 归一化幅度、计数 | 实/整数标量 |
| $a,r_i$ | 实际网格幅度与单位模原序列 | a模长beta/sqrt(P)；r模长1 | 归一化复幅度 | 网格[P,L,K]、原序列[M*n_symbols,P] |

generate 输出 r；map_to_grid 输出 a。beta 默认1，外部可用其表示功控给定的线性幅度；未实现 TS 38.213 闭环功控计算。beta=0 时 RE 仍标为占用。

**S10，项目坐标推导，依据 §4.4.4.1/3/4/5 与 §6.4.1.4.3。**

$$
k_{BWP,low}=12(bwp\_start-n\_start\_grid),\quad
CRB=n\_start\_grid+\lfloor k/12\rfloor.
$$

**变量说明（项目辅助表，范围以本式上下文为准）**

| 符号/代码变量 | 含义与作用 | 取值范围/约束 | 单位 | 维度/类型 |
|---|---|---|---|---|
| $k_{BWP,low}$ | BWP第一个子载波的载波局部坐标 | 12*(bwp_start-n_start_grid)，0..K-12 | 子载波索引 | 整数标量 |
| $bwp\_start,n\_start\_grid$ | BWP/载波起始CRB | 满足NRCell包含约束 | RB | 各一整数标量 |
| $k,CRB$ | 载波局部子载波号与其公共RB号 | 0≤k<K；CRB=n_start_grid..n_start_grid+n_size_grid-1 | 子载波/CRB索引 | 整数标量 |

**S11，项目绘图/CSV 频率推导，依据 §4.4.4.2 与 §5.3.1。** Δf 为 Hz；Point A 频偏使用 NRCell.subcarrier_offset_hz。这里 carrier center 指 §5.3.1 的 OFDM 居中参考 k=N_grid_size*12/2，不是最低/最高子载波中心的几何平均：

$$
f_{carrier\ center}=(k-N_{grid}^{size}12/2)\Delta f,\quad
f_{PointA}=(12N_{grid}^{start}+k)\Delta f.
$$

**变量说明（项目辅助表，范围以本式上下文为准）**

| 符号/代码变量 | 含义与作用 | 取值范围/约束 | 单位 | 维度/类型 |
|---|---|---|---|---|
| $f_{carrier\ center}$ | 相对OFDM居中参考k=K/2的频率 | 负频率到正频率，(k-K/2)*SCS | Hz | 每k一个实数 |
| $f_{PointA}$ | 相对Point A子载波0中心的频率 | 本cell起点非负，随k递增 | Hz | 每k一个实数 |
| $k,N_{grid}^{size},N_{grid}^{start}$ | 载波局部k、载波RB宽度、起始CRB | k=0..12*size-1；size1..275；start0..2199 | 索引、RB、RB | 整数标量 |
| $\Delta f$ | SCS，必须用Hz | 15000/30000/60000/120000/240000 | Hz | 实标量 |

这是相对频率，不是绝对 RF 频率，不假定某个中心频点。梳齿间隔为 K_TC*Δf，不能把每个空梳齿当作 SRS 复数序列点。

## 独立验证与边界

[MATLAB 脚本](../../examples/srs/export_NRSRS_reference.m) 独立调用 nrSRS/nrSRSIndices/nrResourceGrid，保存 832 组真实输入与全部向量。已比对 364800 个复数值，坐标零差异，最大序列绝对误差约 1.468e-9；逐点容限 rtol=0、atol=2e-9。详细环境、阈值、测试与限制见 [验证报告](../../documentation/validation/NRSRS_validation.md)。

MATLAB 当前文档包含后续 Release 扩展；适配器和脚本显式关闭定位、频率缩放/部分探测、8端口、comb/cyclic-shift hopping 等功能，且 Python 严格限制 R15 范围。参考：[nrSRS](https://www.mathworks.com/help/5g/ref/nrsrs.html)、[nrSRSIndices](https://www.mathworks.com/help/5g/ref/nrsrsindices.html)、[nrSRSConfig](https://www.mathworks.com/help/5g/ref/nrsrsconfig.html)。

109 个 SRS 单元测试涵盖错误组合、返回副本、端口正交性、手算跳频排列、帧边界、TDD 许可接口、BWP 越界、功率归一化、零幅度占用与原子冲突。单独通过这些测试不代表完整 UE/gNB SRS 协议流程或空口一致性认证。


## NRSRS长度与幅度核对例

24 RB、comb2得到M=144点/端口/符号；2端口、4个SRS符号的generate形状为[576,2]。cyclic_shift=0时两端口移位号为0、4，相位步长为0、pi rad/序列点；beta=1时映射幅度均为1/sqrt(2)。在相同comb上两个端口占用的物理RE集合可以相同，通过参考序列区分端口。
