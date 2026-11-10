# NRDCICode：DCI CRC24C、Polar与速率匹配

[源码](NRDCICode.py)。固定TS38.212 V15.2.0 §7.3.2～4、§5.1/§5.3.1/§5.4.1：24个1前缀的CRC24C、最后16个CRC位与RNTI异或、输入交织、n_max=9 Polar及子块交织/打孔/缩短/重复。无UCI的PC位或编码位交织。接收使用工程SC译码，不是CRC辅助SCL。

| 字段 | 含义、范围、单位、示例 |
|---|---|
| n_bits | DCI payload位数A，整数12..140；例32；字段打包及尺寸对齐由调用方完成 |
| output_length | E，整数A+24..1728，bit；PDCCH为108*聚合等级，例432 |
| rnti=1 | CRC掩码RNTI，整数0..65535，例4321；不自动作为PDCCH加扰RNTI |

构造/__post_init__验证上述范围。n_blocks恒1、crc_length恒24。crc(bits)供内部合法二进制payload使用，返回int8[24]已掩码CRC；不是公共输入校验接口。polar_configuration()返回(k,e,N,j,indices,empty_set)：k=A+24、e=E、N为32..512的2次幂、j为int[N]子块排列、indices为int[k]信息位置、最后是空PC集合。所有索引零基、无量纲，非法/损坏可靠度表抛异常。

encode(bits)要求整数二进制[A]且拒绝bool/float，输出int8[E]。decode(llr)要求有限float[E]、正值支持0，返回bits为A位list及crc_ok为bool；CRC失败仍返回候选位。无HARQ合并、盲长度/RNTI搜索、DCI语义解析或SCL。

文档自编号DCI-1，依据上述固定版本编码规则；子块表来自原表5.4.1.1-1，输入交织表来自原表5.3.1.1-1：

$$
K=A+24,\quad u_{\mathcal I}=\Pi_{IL}([b,CRC24C([1^{24},b])\oplus m_{RNTI}]),\quad
x=uG_N,\quad d_i=x_{J(i)},\quad E=108L.\tag{DCI-1}
$$

b为int[A] payload；m_RNTI为24位掩码、前8位0及后16位MSB优先RNTI；I为int[K]可靠度信息位置；u/x为int8[N]母码输入/输出；G_N为GF(2)蝶形变换，未显式分配矩阵；Pi_IL和J为输入/子块排列；L为聚合等级1/2/4/8/16；E为速率匹配位数。均为bit/索引，无物理功率单位。d再按同版本§5.4.1选择尾部（打孔）、头部（缩短）或循环重复至E，接收按相反规则恢复LLR。

```python
from common.NRDCICode import NRDCICode
c=NRDCICode(32,432,rnti=4321)
b=[0,1]*16
o=c.decode(20*(1-2*c.encode(b)))
assert o['crc_ok'] and o['bits']==b
```

真实MATLAB nrDCIEncode比较并入[整链路验证](../../documentation/validation/NRPDCCH_validation.md)。CRC24C多项式0x1B2B117，最高项含在整数中。编码前缀不作为额外payload传给Polar。

## 逐变量说明

以下变量对应本文已有公式或算法表达式；规范基线和章节沿用对应公式处的引用。每行只定义一个变量，同名符号只在该公式上下文有效。

| 变量 | 含义与用途 | 范围/约束 | 单位 | 维度/类型 |
|---|---|---|---|---|
| A | 原始DCI长度，决定Polar信息长度 | 12..140 | bit数 | 整数标量 |
| K | 载荷加CRC长度，决定信息位数量 | A+24 | bit数 | 整数标量 |
| b | DCI载荷，字段语义由调用者打包 | 每点0/1 | bit | int[A] |
| m_RNTI | CRC掩码，校验关联RNTI | 前8位0，后16位为RNTI的MSB优先二进制 | bit | int[24] |
| I | 信息位位置集合，承载交织后的K位 | 母码域内K个可靠度位置 | bit索引 | int[K] |
| u | 含信息位和冻结位的Polar输入 | 每点0/1，冻结位置为0 | bit | int8[N] |
| x | Polar变换输出母码 | 每点0/1 | bit | int8[N] |
| N | Polar母码长度，决定变换规模 | 2的幂32..512，按码长选择规则 | bit数 | 整数标量 |
| G_N | GF(2)生成变换，实现蝶形编码 | 元素0/1，由核的Kronecker幂构成 | 无量纲 | 概念矩阵[N,N]，实现不显式分配 |
| Pi_IL | 输入交织排列，重排信息与CRC位 | 0..K−1的一一排列，来自固定原表 | bit索引 | int[K] |
| J | 子块交织排列，重排母码位 | 0..N−1的一一排列 | bit索引 | int[N] |
| i | 子块交织输出位索引 | 0..N−1 | bit索引 | 整数标量 |
| d_i | 子块交织后第i个母码位，供打孔/缩短/重复 | 0/1 | bit | 二进制标量 |
| L | PDCCH聚合等级，决定编码预算 | 1/2/4/8/16 | CCE数 | 整数标量 |
| E | 速率匹配后输出长度 | PDCCH为108L；本类还要求E≥A+24 | bit数 | 整数标量 |
