# NRPUCCH2：Format 2物理资源与序列

[源码](NRPUCCH2.py)。固定TS38.211 V15.2.0 §6.3.2.5、§6.4.1.3.2、§5.1。单端口2000，接口逻辑端口0；连续RB、不使用交织或扩频OCC。编码由[NRSmallBlockCode](../common/NRSmallBlockCode.md)负责，资源类generate接收编码位，不把编码位冒称UCI原始位。

| 字段/属性 | 含义、范围、单位与示例 |
|---|---|
| cell | NRCell，当前slot/网格/CP；例NRCell(n_size_grid=12) |
| prb=0 | 第一跳BWP局部起始RB，0..bwp_size-n_prbs，例1 |
| n_prbs=1 | 连续RB数量1..min(16,bwp_size)，例3 |
| start_symbol=0 | slot内零基符号0..slot符号数-n_symbols，例8 |
| n_symbols=1 | 符号数1/2，例2 |
| rnti=1 | 无线网络标识，整数0..65535，例4321 |
| data_scrambling_id=None | 数据加扰ID，0..1023；None解析为PCI，例731 |
| dmrs_scrambling_id=None | DMRS ID，0..65535；None解析为PCI，例271 |
| second_hop_prb=None | None关闭，否则第二跳起始RB，范围同prb且要求两符号；同RB也视为开启 |
| coded_length | E=16*n_prbs*n_symbols，编码位数，无量纲整数 |

构造/`__post_init__`校验字段，冻结配置不可修改。`indices(dmrs=False)`返回int[RE,3]：逻辑端口、slot符号、载波局部子载波。dmrs必须bool；每RB内DMRS位置1/4/7/10，其余8点是数据；数据与DMRS分别先频率、后符号排列。第二个符号映射第二跳（若配置）。

`scrambling()`返回int[E] Gold序列，初始化rnti*2^15+data_scrambling_id。`qpsk(bits)`为内部QPSK映射辅助：调用方提供偶数长度二进制数组；偶数索引映实部，奇数索引映虚部，0对应正号，输出complex[N/2]单位能量。公共generate负责输入二进制校验。

`dmrs()`返回complex[4*n_prbs*n_symbols]单位模DMRS，按固定R15 Gold初始化及CRB0频率原点截取。`generate(coded_bits)`严格要求E个整数0/1，拒绝bool，返回complex[E/2]加扰QPSK数据，不含DMRS。`map_to_grid(grid,coded_bits,beta=1)`要求同小区单端口NRGrid，beta为有限非负线性幅度；合并数据和DMRS后一次写入owner=PUCCH，返回12*n_prbs*n_symbols。非法范围/输入抛校验异常；网格冲突由NRGrid拒绝。

以下F2-1为文档自编号，依据上述规范章节，不冒充原文公式编号：

$$
c_{\mathrm{init}}=\bigl[2^{17}(14n_{\mathrm{slot}}+l+1)(2N_0+1)+2N_0\bigr]\bmod2^{31},\quad
r[m]=\frac{1-2c[2m]+j(1-2c[2m+1])}{\sqrt2}.\tag{F2-1}
$$

| 变量 | 含义、范围、单位、维度 |
|---|---|
| n_slot、l | 帧内slot索引、slot内符号索引，来自cell，整数；l0..slot符号数-1 |
| N_0 | DMRS身份0..65535，整数标量 |
| c_init、c | 31位初始化整数、Gold位流int数组；无量纲 |
| m | 从CRB0开始的DMRS序列索引，目标起点4*(bwp_start+当前跳prb) |
| r | DMRS单位模复序列，归一化幅度 |
| j | 虚数单位，无量纲 |

```python
from cell import NRCell
from pucch import NRPUCCH2
r = NRPUCCH2(NRCell(n_size_grid=12), n_prbs=3, n_symbols=2, second_hop_prb=6)
assert r.coded_length == 96
```

普通CP已MATLAB实测；扩展CP物理链路已Python测试，固定14*slot寻址尚无本模块MATLAB独立扩展CP向量。资源分配/maxCodeRate选择由调度层负责，当前收发类额外限制UCI/E≤0.6。
