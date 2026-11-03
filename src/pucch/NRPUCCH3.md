# NRPUCCH3：Format 3资源、DFT预编码与DMRS

[源码](NRPUCCH3.py)。固定TS38.211 V15.2.0 §5.1/5.2.2、§6.3.2.2、§6.3.2.6及§6.4.1.3.3。单端口2000，数组逻辑端口0。编码由公共NRUCICode处理；本类generate接收已编码位[E]。不同于F1，没有时域OCC；不同于F2，数据在每符号上作单位能量DFT预编码，DMRS占完整符号。

| 字段/属性 | 含义、范围、单位、示例 |
|---|---|
| cell | NRCell，例NRCell(n_size_grid=24) |
| prb=0 | 第一跳BWP局部起始RB，0..bwp_size-n_prbs，例1 |
| n_prbs=1 | 带宽，允许1/2/3/4/5/6/8/9/10/12/15/16，且须在BWP内；例3 |
| start_symbol=0 | slot内零基起始符号，0..slot符号数-n_symbols，例1 |
| n_symbols=14 | 符号数4..slot符号数；扩展CP需显式指定≤12 |
| rnti=1 | 0..65535整数，例4321 |
| data_scrambling_id=None | 数据ID0..1023，None解析PCI，例731 |
| hopping_id=None | DMRS序列ID0..1023，None解析PCI，例271 |
| group_hopping='neither' | neither/enable/disable；disable为序列跳变，仅长度≥72可能v=1 |
| second_hop_prb=None | 第二跳BWP局部起始RB；None关闭，同RB也启用跳频 |
| additional_dmrs=False | 严格bool，开启额外DMRS；长度<10时按原表位置不额外增加 |
| modulation='QPSK' | QPSK或pi/2-BPSK |
| dmrs_symbols | 相对DMRS符号int[D]，原表6.4.1.3.3.2-1，范围0..n_symbols-1 |
| data_symbols | 非DMRS相对符号int[S]，S=n_symbols-D |
| coded_length | E=Qm*12*n_prbs*S，编码位数；Qm=2或1 |

构造/`__post_init__`校验上述类型/范围，冻结配置。`indices(dmrs=False)`返回int[RE,3]：端口0、slot符号、载波局部子载波；dmrs必须bool，选择数据或DMRS；先频率后符号。跳频分界floor(n_symbols/2)，DMRS位置仍按全资源相对符号。4符号时无跳频DMRS=[1]，跳频=[0,2]；其余全部位置依据原表，非经验插入。

`scrambling()`按RNTI*2^15+dataID生成Gold int[E]。`generate(coded_bits)`校验严格整数二进制[E]，加扰后QPSK或π/2-BPSK调制，再按每数据符号12*n_prbs点单位化DFT，返回complex[S*12*n_prbs]。π/2-BPSK的交替相位索引沿连续数据调制符号计数，不随跳频或DMRS重置。

`dmrs()`返回complex[D*12*n_prbs]。12/24点使用固定相位表，≥36使用最大较小素数的Zadoff–Chu扩展；逐符号Gold循环移位m0=0、m_cs=0，按每跳的组/序列跳变生成u/v。未将DMRS进行额外DFT；参考已经定义于频域。24点共享表在common/_low_papr_24.json，数值与已有SRS原表相同。

`map_to_grid(grid,coded_bits,beta=1)`要求同小区单端口NRGrid；beta为有限非负线性幅度，数据/DMRS同幅；合并坐标后原子写owner=PUCCH，返回12*n_prbs*n_symbols。冲突遵守NRGrid检查。错误输入/范围抛相应校验异常。

文档自编号F3-1，依据TS38.211 V15.2.0 §6.3.2.6.4：

$$
z_{s,k}=\frac1{\sqrt M}\sum_{m=0}^{M-1}d_{s,m}e^{-j2\pi mk/M},\qquad M=12P.\tag{F3-1}
$$

| 变量 | 含义、范围、单位、维度 |
|---|---|
| P、M | 资源RB数、每符号DFT长度，整数标量，M12..192 |
| s、m、k | 数据符号索引0..S-1、DFT输入/输出索引0..M-1 |
| d、z | 调制符号/预编码频域符号，complex[S,M]，归一化复幅度 |
| j | 虚数单位；单位化DFT保持各符号总能量 |

```python
from cell import NRCell
from pucch import NRPUCCH3
r = NRPUCCH3(NRCell(n_size_grid=24), n_prbs=3, n_symbols=12,
             second_hop_prb=12, additional_dmrs=True)
assert r.coded_length == 576
```
