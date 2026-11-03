# NRPUSCH：首版单层CP-OFDM资源与序列

[源码](NRPUSCH.py)。固定TS38.211 V15.2.0 §5.1/5.2.1、§6.3.1.1～6、§6.4.1.1.1.1/6.4.1.1.3。单码字、单层、逻辑端口0及DMRS端口0，连续PRB，无跳频；Type-A、Type-1单符号DMRS，AdditionalPosition=0，关闭变换预编码/PTRS/UCI复用。未实现功能没有伪配置字段，不应将本类描述为完整R15 PUSCH。

| 字段/属性 | 含义、范围、单位、示例 |
|---|---|
| cell | NRCell，例NRCell(n_size_grid=12) |
| prb=0 | BWP局部起始RB，0..bwp_size-n_prbs，例1 |
| n_prbs=4 | 连续RB数1..bwp_size |
| start_symbol=0 | slot内零基起始符号，0..min(3,slot符号数-n_symbols)，例1 |
| n_symbols=14 | 占用符号数4..slot符号数，扩展CP需显式指定≤12 |
| rnti=1 | 整数0..65535，例4321 |
| data_scrambling_id=None | 数据ID0..1023，None解析PCI，例731 |
| dmrs_scrambling_id=None | DMRS ID0..65535，None解析PCI，例271 |
| n_scid=0 | DMRS初始化选择0/1；ID已由调用方选择为本字段对应值 |
| dmrs_type_a_position=2 | slot内DMRS符号2或3；必须在资源中 |
| cdm_groups_without_data=1 | 1或2；1时DMRS符号奇数子载波可放数据，2时整个DMRS符号不放数据 |
| modulation='QPSK' | QPSK/16QAM/64QAM/256QAM |
| modulation_order | Qm=2/4/6/8，调制每符号位数 |
| coded_length | G=数据RE数量*Qm，编码位数 |

构造和`__post_init__`校验字段，冻结配置；非法类型/范围抛校验异常。`indices(dmrs=False)`返回int[RE,3]，列为端口0、slot符号、载波局部子载波，先频率后符号。dmrs严格bool；Type1端口0占DMRS符号的偶数RB局部子载波，每RB6点；CDM组2额外保留的奇数RE不映射数据，也不伪造另一个端口的DMRS。

`scrambling()`返回Gold int[G]，初始化RNTI*2^15+dataID，码字q=0。`constellation()`返回(complex[2^Qm],int8[2^Qm,Qm])：规范Gray标记QAM点及对应比特，归一化平均能量1。比特索引0/2/4/6映I、1/3/5/7映Q。`generate(coded_bits)`严格校验整数二进制[G]，加扰后QAM映射，输出complex[G/Qm]，不含DMRS。

`dmrs()`返回complex[6*n_prbs]单位模Gold-QPSK参考，CRB0为频率原点，起点序列索引6*(bwp_start+prb)。使用实际cell.symbols_per_slot寻址PUSCH DMRS，不沿用PUCCH的固定14规则。`map_to_grid(grid,coded_bits,beta=1)`要求同cell单端口NRGrid，beta有限非负线性幅度，数据/DMRS同幅，一次原子写owner=PUSCH；返回实际映射RE数量，不包括仅保留的CDM组RE。

文档自编号PUSCH-1，依据TS38.211 V15.2.0 §6.4.1.1.1.1：

$$
c_{\rm init}=\bigl[2^{17}(N_{\rm symb}^{\rm slot}n_{\rm slot}+l+1)(2N_{\rm ID}+1)+2N_{\rm ID}+n_{\rm SCID}\bigr]\bmod2^{31}.\tag{PUSCH-1}
$$

| 变量 | 含义、范围、单位、维度 |
|---|---|
| c_init | Gold初始化整数0..2^31-1，无量纲标量 |
| N_symb_slot、n_slot、l | slot符号数14/12、帧内slot索引、DMRS符号2/3，无量纲整数标量 |
| N_ID、n_SCID | 已选择DMRS ID0..65535、初始化选择0/1 |
| G、Qm、RE | 编码位数、每QAM符号位数、资源网格元素计数，整数标量 |

```python
from cell import NRCell
from pusch import NRPUSCH
r = NRPUSCH(NRCell(n_size_grid=12), prb=1, n_prbs=4, n_symbols=12,
             modulation='16QAM', cdm_groups_without_data=1)
assert len(r.dmrs()) == 24
```

Type-B、Type-2/双符号/额外DMRS、多端口、多层码本/RI/TPMI、DFT-s-OFDM、跳频、PTRS、UCI复用、MCS/TBS自动选择和调度均待扩展。扩展CP/非零起始符号目前有Python测试，实际MATLAB独立范围见验证报告。
