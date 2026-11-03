# NRUCICode：PUCCH公共UCI编码链

[源码](NRUCICode.py)。固定TS38.212 V15.2.0 §5.1、§5.2.1、§5.3.1、§5.3.3.3、§5.4.1/3、§6.3.1.2～5。用于PUCCH2/3/4的UCI位流；不负责HARQ/SR/CSI字段拼接、调度和信道映射。复用NRSmallBlockCode及NRPolarCode.transform。经典RM(r,m)与NR小块码不是同一接口；LDPC不用于PUCCH。

| 字段/属性 | 含义、范围、单位、示例 |
|---|---|
| n_bits | 输入UCI位数A，整数3..1706，例32 |
| output_length | 速率匹配位数E，整数A..32768；双码块时要求偶数；实际信道受资源限制，例192 |
| crc_length | A3..11返回0，12..19返回6，20以上返回11，单位bit |
| n_blocks | C，整数1/2；A≥1013或A≥360且E≥1088时为2 |

自动构造和`__post_init__`校验上述范围。`encode(bits)`要求整数二进制[A]，输出int8[E]；拒绝bool、形状错误或非法位。A≤11调用小块码编码/截取重复；A≥12依次完成前置零填充分段、每块CRC6/11、Polar信息/冻结/PC位分配、蝶形变换、子块交织、比特选择及三角交织。分段后每块输出floor(E/C)位；双码块时要求E为偶数，因此两块整除；单块允许奇数E，支持F4 π/2-BPSK、SF4的资源长度。

`decode(llr)`接收有限float[E]，正支持0；小块码软ML，Polar反三角交织、重复软累加或打孔补0/缩短补强0约束，再PC约束SC译码、检查每块CRC并去掉前置分段填充。返回dict：bits为整数[A] list；crc_ok在无CRC的小块码为None，Polar为所有码块CRC是否通过的严格bool。CRC失败仍返回判决位，调用方必须检查crc_ok。未进行CRC辅助SCL或错误重传；SC性能不能等同Toolbox SCL。

`crc(bits,length)`静态内部辅助：length仅用于本类CRC6/11调用，生成初态0、无掩码的多项式余数int8[length]；多项式分别x^6+x^5+1及x^11+x^10+x^9+x^5+1。调用方不要将它当成任意CRC工具。

`polar_configuration()`返回(k,e,N,j,information,pc)：k为每块含CRC位数，e为每块E；N为32..1024的2次幂；j是原表5.4.1.1-1子块交织索引int[N]；information为排序信息加PC索引int[k+n_PC]；pc为PC位索引set[int]。18≤k≤25使用3个PC位，其余支持区间使用0；当e-k+3>192时使用一个最小行重PC位。资源不足抛ValueError。N、冻结位置和打孔/缩短规则均按固定规范，不把母码最可靠k位直接用于所有E。

`bit_interleaver(e)`静态内部辅助返回三角交织置换int[e]，索引0..e-1。SUBBLOCK常量为原表5.4.1.1-1的32项置换，不是项目经验表。

以下UCI-1为文档自编号，依据上述固定章节，用于说明维度而非冒充规范原式：

$$
A'=C\lceil A/C\rceil,\quad k=A'/C+L_{\rm CRC},\quad e=E/C,\quad
u_{\cal F}=0,\quad x=uG_N.\tag{UCI-1}
$$

| 变量 | 含义、范围、单位与维度 |
|---|---|
| A、A'、C | 原始位数、前置0填充后的位数、码块数；无量纲整数标量，A'-A为0/1 |
| L_CRC、k、e | 每块CRC位数0/6/11、信息加CRC长度、输出长度，单位bit |
| N、u、x | 母码长度、变换前/后母码，N32..1024，u/x为二进制[N] |
| F | 冻结位置集合，整数索引0..N-1；PC位不是冻结位 |
| G_N | 二元Polar生成矩阵，[N,N]；实际计算使用蝶形，无需存完整矩阵 |
| llr | 无量纲软输入float[E]；白噪声下等比例缩放不改变SC符号判决 |

```python
from common import NRUCICode
codec = NRUCICode(32, 192)
bits = [0, 1]*16
result = codec.decode(20*(1-2*codec.encode(bits)))
assert result['bits'] == bits and result['crc_ok']
```

MATLAB实际15例覆盖小块、CRC6/11、两种PC分配、打孔/缩短/重复、分段及A1706。该对比是码字及无噪译码一致性，不是低SNR性能保证。
