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
