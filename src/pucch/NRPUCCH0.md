# NRPUCCH0：R15 Format 0资源与序列

[NRPUCCH0.py](NRPUCCH0.py)表示单个UE在当前NRCell时隙上的一个PUCCH Format 0资源，生成HARQ-ACK/SR对应的循环移位序列，并通过NRGrid映射。只有一个逻辑端口：协议端口2000对应数组端口0；物理发送天线数不决定逻辑端口数。

固定基线：**TS38.211 V15.2.0 §5.2.1、§5.2.2.2表5.2.2.2-2、§6.3.2.2/3**；UCI到循环移位映射依据 **TS38.213 V15.3.0 §9.2.3、§9.2.4、§9.2.5.1**。下面F0-1至F0-3是本文自编号，不是规范原公式号。变量约定见[指南](../../documentation/formula_reference.md#conventions)。

## 功能边界

支持0..2 HARQ-ACK位、可选单个SR、1/2个OFDM符号、单RB、normal/extended CP、组跳变与2符号时隙内跳频。normal/extended均按固定R15的14*slot循环移位寻址。显式提供PRB/符号分配，不实现DCI资源指示、HARQ码本拼装、SR机会调度、TDD许可、闭环功控、跨slot重复或交织；格式1/2/3/4后续使用独立类。

`group_hopping='disable'`意味着开启序列跳变，可能得到v=1；12点基序列在§5.2.2只定义v=0，因此当前F0配置明确拒绝该模式。`neither`和`enable`均支持；不是把disable静默当neither。

## 每个字段

冻结slots dataclass，无其他隐藏状态/类常量。

| 字段 | 用途 | 范围/单位/维度 | 示例 |
|---|---|---|---|
| cell | 当前小区、BWP、slot、CP与采样率来源 | 必须NRCell，不可None | `NRCell(n_size_grid=24)` |
| prb=0 | 第一跳RB号，相对活动BWP | Python int，0..cell.bwp_size-1；RB索引标量 | BWP CRB12起，prb1对应CRB13 |
| start_symbol=None | 首个slot局部符号号 | None解析为L-n_symbols；0..L-n_symbols | 2符号normal默认12 |
| n_symbols=1 | F0持续符号数 | Python int 1/2；符号计数标量 | 2 |
| initial_cyclic_shift=0 | 初始移位m0 | Python int 0..11，无量纲移位号 | 5 |
| hopping_id=None | Gold/基序列组使用的ID | None解析为cell.n_cell_id；显式0..1023 | 731，不要求等于PCI |
| group_hopping='neither' | 基序列组跳变 | 'neither'/'enable' | 'enable' |
| second_hop_prb=None | 第二符号跳到的BWP局部RB | None不跳频；非None需n_symbols=2，0..BWP_size-1 | 17；允许与第一跳相同RB |

整数拒绝bool、浮点及NumPy整数，沿用项目严格Python int规则。cell类型错误TypeError；数值范围、CP内符号越界及不支持的配置报ValueError。

## HARQ-ACK/SR原表

输入HARQ比特按给定顺序；0=NACK，1=ACK。sr=None表示本次不传SR，sr=0/1表示负/正SR。下面是原表数值的辅助汇总，不重新定义协议。

| HARQ-ACK | 无SR/负SR时m_cs | 正SR时m_cs | 规范原章节与表号 |
|---|---|---|---|
| [0] | 0 | 3 | TS38.213 V15.3.0 §9.2.3表9.2.3-3；§9.2.5.1表9.2.5-1 |
| [1] | 6 | 9 | 同上 |
| [0,0] | 0 | 1 | 同版本§9.2.3表9.2.3-4；§9.2.5.1表9.2.5-2 |
| [0,1] | 3 | 4 | 同上 |
| [1,1] | 6 | 7 | 同上 |
| [1,0] | 9 | 10 | 同上 |
| 无HARQ | 负SR为DTX，不发送 | 0 | 同版本§9.2.4正文，无独立原表 |

例：[1,0]+正SR的m_cs=10，不能把[1,0]当二进制2再乘3。空HARQ且sr=None没有可发送信息，报ValueError。负SR-only的generate返回空数组，映射不占用任何RE；负SR与HARQ同时存在时仍发送HARQ。

## 序列与映射公式

**F0-1**，依据TS38.211 V15.2.0 §6.3.2.2.1/2、§5.2.1：

$$
t=14n_{slot}+l_0+l',\quad n_{cs}(t)=\sum_{m=0}^{7}2^m c(8t+m),\quad
s_{l'}=(m_0+m_{cs}+n_{cs}(t))\bmod12,\quad \alpha_{l'}=2\pi s_{l'}/12.
$$

| 变量 | 含义 | 范围/单位 | 维度 |
|---|---|---|---|
| n_slot、l0、l_prime | 帧内slot、资源slot起始符号、资源内符号 | slot在帧内；0≤l0≤L-S；l_prime0..S-1 | 整数标量 |
| S、L | F0符号数、每slot符号数 | S1/2，Lnormal14/extended12；符号计数 | 整数标量 |
| t、m、c | R15固定14寻址位置、8bit位权号、Gold序列 | t非负，m0..7，c0/1；位置是bit/符号索引 | 标量、比特序列 |
| n_cs、m0、m_cs、s | 8bit跳变量、初始移位、UCI移位、最终移位 | n_cs0..255，其余0..11；无量纲 | n_cs和s为[S]，m0/mcs标量 |
| alpha | 逐序列点相位增量 | 0≤alpha<2*pi，rad/点 | [S] |

循环移位Gold种子为hopping_id，每帧重置。组跳变采用另一种子floor(hopping_id/30)，在跳段n_hop=0/1处读取8bit，u=(fgh+hopping_id)mod30；无跳频两个符号的n_hop都为0，第二符号不是默认第二跳。更细寻址及返回值见[NRCommon](../common/NRCommon.md)。

**F0-2**，依据同版本§5.2.2.2表5.2.2.2-2、§6.3.2.3.1：

$$
x(12l'+n)=\exp(j\varphi_{u_{l'}}(n)\pi/4)\exp(j\alpha_{l'}n),\quad n=0,\ldots,11.
$$

| 变量 | 含义 | 范围/单位 | 维度 |
|---|---|---|---|
| x | 未乘beta的F0序列，先频率后符号排列 | 单点模长1，归一化复幅度 | [12*S] |
| u、v | 基序列组与组内编号 | u0..29，F0仅v=0；无量纲 | 每符号一个，数组[S] |
| phi_u | 固定原表的相位系数 | -3/-1/1/3，乘pi/4得到rad | 原表[30,12]；选中行[12] |
| n、l_prime | RB内子载波/序列位置与资源内符号 | n0..11，l_prime0..S-1 | 整数标量 |
| j、alpha | 虚数单位、F0-1相位步长 | j²=-1；rad/点 | 复常量、每符号实标量 |

**F0-3**，依据同版本§6.3.2.3.2及§4.4.4.4/§4.4.5：

$$
k=12(N_{BWP}^{start}-N_{grid}^{start}+PRB_{l'})+n,\quad
l=l_0+l',\quad a_{k,l}^{(2000)}=\beta x(12l'+n).
$$

| 变量 | 含义 | 范围/单位 | 维度 |
|---|---|---|---|
| N_BWP_start、N_grid_start | BWP/载波起点，均相对CRB0 | 依NRCell约束；CRB索引 | 两个整数标量 |
| PRB_l_prime | 当前跳的BWP局部RB号 | 0..BWP_size-1 | 每符号一个整数 |
| k、l、n | 载波局部频率号、slot符号号、RB内号 | k0..K-1、l0..L-1、n0..11 | 每RE坐标 |
| beta、a、x | 线性发送幅度、网格复数、原序列 | beta非负有限；a模长beta；不是dBm | beta标量、网格[1,L,K]、序列[12*S] |

## 每个方法及返回值

| 方法 | 参数、返回与示例 |
|---|---|
| 自动__init__、__post_init__ | 初始化上表字段，解析None，校验1RB资源完全在BWP与slot内 |
| cyclic_shift_offset(harq_ack=(),sr=None) | 静态映射UCI到m_cs，返回int或None(DTX)；`NRPUCCH0.cyclic_shift_offset([1,0],1)==10` |
| sequence_parameters(m_cs=0) | 返回u/v/hop/n_cs/cyclic_shift/alpha字典，每个值[S]新数组；alpha为rad，其余int64 |
| generate(harq_ack=(),sr=None) | 新complex128[12*S]；负SR-only为空[0]；每个元素未乘beta |
| indices() | 新int64[12*S,3]，列为[端口0,slot符号,载波局部k]；配置资源坐标与负SR是否实际发送无关 |
| map_to_grid(grid,harq_ack=(),sr=None,beta=1) | grid须同cell且仅1端口；owner='PUCCH'，调用NRGrid原子映射；返回实际写入RE数；冲突报ValueError |
| to_dict() | JSON兼容字典，包含已解析配置及antenna_port=2000；不是MATLAB配置对象 |
| 内部_harq_ack(bits) | 一维tuple/list/整数ndarray→tuple，长度0..2、值0/1；拒绝bool/float/二维，不改变HARQ位序 |

## 可运行示例

```python
from cell import NRCell
from grid import NRGrid
from pucch import NRPUCCH0

cell=NRCell(n_size_grid=24,bwp_start=2,bwp_size=20)
resource=NRPUCCH0(cell,prb=1,start_symbol=10,n_symbols=2,second_hop_prb=17)
grid=NRGrid(cell)
assert resource.map_to_grid(grid,[1,0],sr=1)==24
assert resource.generate([1,0],1).shape==(24,)
assert resource.indices()[0,2]==36
```

[发射机](NRPUCCH0Transmitter.md)、[接收机](NRPUCCH0Receiver.md)、[完整示例](../../examples/pucch/README.md)。[实际MATLAB比对与扩展CP适配说明](../../documentation/validation/NRPUCCH0_validation.md)。
