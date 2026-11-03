# NRPUCCH1：Format 1资源、数据与DMRS

[源码](NRPUCCH1.py)。固定TS38.211 V15.2.0 §5.1、§6.3.2.2、§6.3.2.4及§6.4.1.3.1。输入是已确定资源上的1/2个UCI位；不实现SR资源选择、跨slot重复、调度或功控。逻辑端口0对应协议端口2000。

## 字段

| 字段/默认值 | 含义、范围、单位 | 示例 |
|---|---|---|
| cell | NRCell，小区/当前slot/CP/采样配置 | NRCell(n_size_grid=6) |
| prb=0 | BWP局部RB索引，0..bwp_size-1 | 1 |
| start_symbol=0 | slot内零基符号索引，0..symbols_per_slot-n_symbols | 1 |
| n_symbols=14 | 连续资源符号数，4..slot符号数 | extended CP需显式指定12或更少 |
| initial_cyclic_shift=0 | 初始移位，整数0..11 | 3 |
| hopping_id=None | 序列身份0..1023；None解析为PCI | 731 |
| group_hopping='neither' | neither或enable；当前不接受disable | enable |
| second_hop_prb=None | None关闭跳频，否则为第二跳BWP局部RB；即使等于prb也启用跳频 | 4 |
| time_domain_occ=0 | 时域OCC索引，必须小于每跳数据及DMRS各自最小符号数 | 1 |
| hops属性 | 每资源符号跳号，整数[L]，0/1；L=n_symbols | 14符号跳频时前7为0、后7为1 |

## 方法与映射

构造及`__post_init__`校验字段，非法范围抛ValueError，错误小区类型抛TypeError。冻结dataclass不允许修改配置。

`modulate(bits)`静态方法：1/2个整数位，拒绝bool和非二进制值；返回单位能量复标量。1bit BPSK的两个点为±(1+j)/√2；2bit QPSK实部由第0位、虚部由第1位决定，0对应正、1对应负。无量纲归一化幅度。

`reference()`返回complex[L,12]，轴为资源相对符号l、RB内子载波n；包含逐符号循环移位和OCC，尚未乘UCI。公共Gold寻址固定14*slot，扩展CP物理slot仍为12符号。`generate(bits)`返回同形状数据与DMRS：相对偶数符号0/2/4…为DMRS，奇数符号1/3/5…乘调制符号d。

`indices()`返回int[12L,3]，列为端口0、slot符号、载波局部子载波，频率先变化。跳频分界为floor(L/2)，与数据/DMRS全局奇偶保持一致。

`map_to_grid(grid,bits,beta=1)`要求同cell、单端口NRGrid；beta为有限非负线性幅度，无量纲；全部数据/DMRS同幅写入owner=PUCCH，返回12L。错误网格抛ValueError，重叠映射遵守NRGrid冲突规则。

OCC依据TS38.211 V15.2.0表6.3.2.4.1-1/-2，DMRS依据表6.4.1.3.1.1-1。数据/DMRS在每一跳分别计数并重新开始OCC索引。N=4使用原表Walsh顺序，不能用4点DFT代替。其余N=1/2/3/5/6/7对应原表复指数码。

下面为文档自编号F1-1，概括上述规范章节的序列构造，不冒充原文公式编号：

$$
x_{l,n}=w_i(m_l)r_l[n]\begin{cases}1,&l\text{为偶数},\\d,&l\text{为奇数}.\end{cases}\tag{F1-1}
$$

| 变量 | 含义、范围、单位、维度 |
|---|---|
| l、n | 相对符号0..L-1、子载波0..11，整数索引 |
| i、m_l | OCC索引、当前跳内同类型符号序号，整数标量；DMRS和数据独立计数 |
| w_i | 单位模时域覆盖码，complex[N]；N为该跳该类型符号数，1..7 |
| r_l | 已加循环移位的基础序列，complex[12]，归一化单位模 |
| d | 单位能量BPSK/QPSK复标量 |
| x | 数据/DMRS资源序列，complex[L,12]，归一化幅度 |

```python
from cell import NRCell
from pucch import NRPUCCH1
r = NRPUCCH1(NRCell(n_size_grid=6), prb=1, n_symbols=12,
             second_hop_prb=4, time_domain_occ=1)
symbols = r.generate([0, 1])
```

[实际MATLAB验证](../../documentation/validation/NRPUCCH1_validation.md)。
