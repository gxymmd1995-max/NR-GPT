# NRPDCCH：CORESET及显式候选

[源码](NRPDCCH.py)。固定TS38.211 V15.2.0 §7.3.2、原表7.3.2.1-1，§7.4.1.3。单逻辑端口2000，QPSK；每CCE含6REG，每REG含一RB一符号的12RE，其中1/5/9为DMRS，9个数据RE。每CCE编码长度108bit。

| 字段/默认值 | 含义、范围、单位及示例 |
|---|---|
| cell | NRCell；例NRCell(n_size_grid=24,n_rx_antennas=2)；首版BWP起点须6CRB对齐 |
| frequency_resources=(0,1) | 有序唯一tuple，元素0..44；每元素表示相对BWP起点的六RB组，支持不连续组，例(0,2)；须在BWP内 |
| duration=2 | CORESET符号数1..3；R15持续3符号时必须dmrs_type_a_position=3 |
| start_symbol=0 | slot内起始符号0..symbols_per_slot-duration |
| aggregation_level=1 | 聚合等级L=1/2/4/8/16，CCE数，原表7.3.2.1-1 |
| cce_start=0 | 已选择候选的首CCE，0..n_cce-L且L对齐；不是候选序号 |
| mapping_type='noninterleaved' | 'noninterleaved'或'interleaved' |
| reg_bundle_size=6 | REG束大小；duration1允许2/6，duration2/3允许duration/6；非交织实际强制使用6 |
| interleaver_size=2 | R为2/3/6，交织时n_regs/(bundle*R)须整数 |
| shift_index=0 | 显式交织移位0..274；CORESET0的PCI回退须由调用方提供，本类不隐式调度CORESET0 |
| scrambling_id=1 | DMRS与数据加扰ID，0..65535；回退PCI时显式传cell.n_cell_id |
| scrambling_rnti=1 | 物理数据加扰RNTI，0..65535；公共搜索空间按规范传0，不与CRC掩码RNTI混同 |
| dmrs_reference_rb=0 | DMRS频率原点CRB，0..CORESET最低CRB；通常0，PBCH/SIB1场景显式传最低CRB |
| dmrs_type_a_position=2 | 固定R15 CORESET持续3符号的配置约束字段2/3 |

构造/__post_init__检查字段和候选边界，不实现TS38.213 SearchSpace候选哈希、监测周期、CORESET0表或DCI字段语义。调用方负责当前候选的发送许可及ID规则。n_regs=6*组数*duration，n_cce=n_regs/6，coded_length=108*L，均整数标量。

regs()返回按符号、频率排序的6L个(symbol,carrier_local_RB)元组，REG编号内部按时间优先。indices(dmrs=False)严格bool，返回int[RE,3]（端口0、slot符号、载波局部子载波），数据54L行、DMRS18L行；排序同映射序列。scrambling()返回int[E] Gold序列。generate(bits)校验整数二进制[E]，加扰QPSK输出complex[54L]单位模。dmrs()返回complex[18L]，按实际CRB原点截取Gold QPSK。map_to_grid(grid,bits,beta=1)要求同cell单端口NRGrid，beta有限非负线性幅度，原子写owner=PDCCH，无返回值。

公式PDCCH-1/2为文档自编号，依据固定§7.3.2.2/§7.3.2.3及§7.4.1.3：

$$
f(j)=[(j\bmod R)C+\lfloor j/R\rfloor+n_{shift}]\bmod(N_{REG}/B),\quad C=N_{REG}/(BR),\quad c_{data}=(n_{RNTI}2^{16}+N_{ID})\bmod2^{31}.\tag{PDCCH-1}
$$

$$
c_{DMRS}=[2^{17}(14n_{slot}+l+1)(2N_{ID}+1)+2N_{ID}]\bmod2^{31}.\tag{PDCCH-2}
$$

j为输入REG束号0..N_REG/B-1，B为束大小2/3/6，R为交织大小2/3/6，C为正整数列数，f为输出束号；n_shift为shift_index。非交织f(j)=j且B=6。N_REG为CORESET REG数，n_RNTI/N_ID为上述数据RNTI/加扰ID，种子为0..2^31-1整数。n_slot为帧内slot，l为slot内DMRS符号；DMRS初始化使用规范固定14因子。所有变量均无量纲整数；QPSK幅度归一化，无绝对瓦特标定。

```python
from cell import NRCell
from pdcch import NRPDCCH
r=NRPDCCH(NRCell(n_size_grid=24),frequency_resources=(0,1,2,3),aggregation_level=4)
assert r.coded_length==432 and len(r.regs())==24
```

当前DMRS仅映射候选内REG（sameAsREG-bundle）；无allContiguousRBs全CORESET参考、动态波束、多层、非6CRB对齐BWP或SearchSpace盲搜。数据前导/CRC由NRDCICode独立处理。
