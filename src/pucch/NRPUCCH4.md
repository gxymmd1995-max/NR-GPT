# NRPUCCH4：Format 4资源、频域OCC与DMRS

[源码](NRPUCCH4.py)。固定TS38.211 V15.2.0 §6.3.2.6、表6.3.2.6.3-1/-2、§6.4.1.3.3、表6.4.1.3.3.1-1及6.4.1.3.3.2-1。单逻辑端口0对应协议端口2000，带宽固定1RB；编码复用NRUCICode，几何和基础DMRS复用NRPUCCH3。F4是在调制后、12点DFT之前进行OCC扩频，不是对DFT后的RE直接乘OCC。

| 字段/属性 | 含义、范围、单位与示例 |
|---|---|
| cell | NRCell，例NRCell(n_size_grid=6) |
| prb=0 | BWP局部起始RB，0..bwp_size-1，例1 |
| start_symbol=0 | slot内零基符号，0..slot符号数-n_symbols，例1 |
| n_symbols=14 | 占用连续符号数4..slot符号数，扩展CP需显式指定≤12 |
| rnti=1 | 数据加扰RNTI，整数0..65535，例4321 |
| data_scrambling_id=None | 数据ID0..1023，None解析PCI，例731 |
| hopping_id=None | DMRS ID0..1023，None解析PCI，例271 |
| group_hopping='neither' | neither/enable/disable；1RB短序列的disable不产生长序列v跳变 |
| second_hop_prb=None | 第二跳BWP局部RB，范围同prb，None关闭；同RB也启用跳频 |
| additional_dmrs=False | 严格bool，按原表选择额外DMRS位置 |
| modulation='QPSK' | QPSK或pi/2-BPSK |
| spreading_factor=2 | SF，整数2或4 |
| occ_index=0 | OCC索引整数0..SF-1，例SF4的3 |
| n_prbs | 只读属性，固定返回1，不能作为构造参数 |
| dmrs_symbols、data_symbols | 相对资源符号索引int[D]、int[S]，范围0..n_symbols-1 |
| coded_length | E=Qm*12*S/SF，位数；Qm=2/1，π/2-BPSK且SF4时可能为奇数 |

构造及`__post_init__`通过共享几何检查字段、解析默认ID，并检查SF/OCC；非法输入抛相应校验异常。配置冻结，不允许后续修改。`base_resource()`返回n_prbs=1的NRPUCCH3共享配置，只用于几何、DMRS基础序列；不能直接用其coded_length代替F4的E。

`indices(dmrs=False)`返回int[RE,3]，列为端口0、slot符号、载波局部子载波；先频率后符号。dmrs必须bool。跳频分界floor(n_symbols/2)；4符号时无跳频DMRS为[1]、跳频为[0,2]，其余位置来自固定原表。`scrambling()`返回int[E]，Gold种子为rnti*2^15+data_scrambling_id。

`occ()`返回complex[12]，按下面原表的短块重复展开，每个短块长度为12/SF。所有元素单位模，不引入1/sqrt(SF)幅度缩放。

| SF | OCC索引 | 每个连续块的系数 | 原文依据 |
|---|---|---|---|
| 2 | 0 | 1、1 | TS38.211 V15.2.0表6.3.2.6.3-1 |
| 2 | 1 | 1、-1 | 同上 |
| 4 | 0 | 1、1、1、1 | TS38.211 V15.2.0表6.3.2.6.3-2 |
| 4 | 1 | 1、-j、-1、j | 同上；注意虚数相位顺序 |
| 4 | 2 | 1、-1、1、-1 | 同上 |
| 4 | 3 | 1、j、-1、-j | 同上 |

`spread(symbols)`输入有限complex[S,12/SF]，按块复制调制数据并乘OCC，返回complex[S,12]。`despread(symbols)`输入IDFT后的有限complex[S,12]，乘共轭OCC、按SF个连续块合并并除SF，返回complex[S,12/SF]。这两个方法不执行DFT/IDFT，便于单独验证OCC和多用户正交性。

`generate(coded_bits)`严格校验整数二进制[E]、拒绝bool；加扰后QPSK/π/2-BPSK调制，π/2交替相位沿连续数据调制符号计数，OCC复制不推进相位计数；扩频后每数据符号做12点单位化DFT，返回complex[12S]，不含DMRS。

`dmrs()`返回complex[12D]，在基础序列逐符号循环移位上增加OCC对应m0。SF2的m0为[0,6]，SF4为[0,6,3,9]，依据TS38.211 V15.2.0表6.4.1.3.3.1-1。不能把OCC系数直接当成DMRS循环移位，也不能简单用3*occ_index代替原表。

`map_to_grid(grid,coded_bits,beta=1)`要求同cell单端口NRGrid；beta为有限非负线性幅度，数据和DMRS同幅，原子写入owner=PUCCH，返回12*n_symbols。网格冲突由NRGrid检查。

文档自编号F4-1，依据上述固定版本§6.3.2.6.3/4：

$$
y_{s,k}=w_i[k]d_{s,k\bmod K},\quad K=12/F,\quad
z_s=\operatorname{DFT}_{12}(y_s)/\sqrt{12},\quad
\widehat d_{s,m}=\frac1F\sum_{b=0}^{F-1}w_i^*[bK+m]\widehat y_{s,bK+m}.\tag{F4-1}
$$

| 变量 | 含义、范围、单位与维度 |
|---|---|
| F、i、K | SF2/4、OCC索引0..F-1、每数据符号未扩频点数6/3，整数标量 |
| s、k、m、b | 数据符号、扩频点、原始点、复制块索引；0..S-1、0..11、0..K-1、0..F-1 |
| d、y、z | 调制数据complex[S,K]、扩频数据complex[S,12]、DFT输出complex[S,12]，归一化复幅度 |
| w_i | 单位模OCC，complex[12]；星号为共轭 |
| y_hat、d_hat | 接收IDFT后的估计、OCC解扩估计；形状同对应发送量 |

```python
from cell import NRCell
from pucch import NRPUCCH4
r = NRPUCCH4(NRCell(n_size_grid=6), spreading_factor=4, occ_index=3,
             n_symbols=12, additional_dmrs=True)
assert r.coded_length == 48
```

OCC可用于同资源用户复用，但不同用户需共享兼容几何/基础序列且信道近似平坦，用户间残余频偏/不同步/频率选择性会造成泄漏；类本身不是调度器或联合多用户均衡器。
