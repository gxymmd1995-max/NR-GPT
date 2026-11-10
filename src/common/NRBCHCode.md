# NRBCHCode：BCH/PBCH载荷与Polar编解码

[源码](NRBCHCode.py)。固定TS38.212 V15.2.0 §7.1.1～5、原表7.1.1-1与7.1.2-1，公共Polar依据§5.3.1/§5.4.1。输入24位BCH传输块（BCCH-BCH/MIB原始比特），补8位时序信息，经载荷交织/选择性加扰、CRC24C、Polar输入交织、N=512/K=56、子块交织和重复匹配，输出E=864位。接收使用SC，非CRC辅助SCL。

## 配置字段

| 字段、默认值 | 含义、范围、单位、示例 |
|---|---|
| cell_id | PCI整数0..1007，例1007；载荷Gold种子 |
| l_max=8 | 半帧候选数4/8/64，整数；由上层按频段选择 |
| ssb_index=0 | SSB索引0..l_max-1；64时高3位写入载荷，例63 |
| half_frame=0 | 半帧位0/1；例1表示广播字段中的后半帧 |
| k_ssb=0 | 0..23，整数；Lmax4/8时仅将其MSB写入追加位，例23写1；Lmax64时不使用此字段 |

构造/__post_init__检查类型、区间及索引边界。NRBCHCode处理编码位，不检查无线频段/时机；NRSSB额外限制Lmax与SSB间隔组合。配置不自动从NRCell.n_frame/n_slot推导，调用方负责广播字段与实际调度一致。

## 输入、输出和方法

encode(mib,sfn_lsb=0)：mib为整数二进制[24]，拒绝bool/float；sfn_lsb为SFN低4位整数0..15。按BCCH-BCH位流约定，mib[1:7]携带SFN高6位；此处不解析ASN.1、构造完整MIB或修改调用方的24位字段。返回int8[864]，尚未做TS38.211的PBCH物理加扰和QPSK。

payload_permutation()返回int[32]，元素为各原始payload位在交织后的位置。SFN位是原输入索引1..6与24..27，半帧位28，额外位29..31；余下18位由原表G[14:32]依次分配。

payload_scrambling(payload)为内部算法接口，输入合法交织后int8[32]，返回复制/异或后的同形数组。SFN第2/3个LSB及半帧位不加扰；Lmax64另有3个索引高位不加扰。再次调用同一函数可解扰，因为决定Gold分段的两个SFN位保持明文。

crc(bits)为内部合法二进制向量的CRC24C余数函数，返回int8[24]。多项式0x1B2B117，初始状态0；与DCI不同，没有24个1前缀和RNTI掩码。不要将NRDCICode直接当作BCH编码器。

decode(llr)要求有限float[864]，正值支持0。先重复合并、逆子块交织、SC/逆输入交织及CRC，再载荷解扰/逆交织。返回字段如下；CRC失败仍给诊断候选，须由调用方检查crc_ok。

| 输出字段 | 含义、范围、单位、维度 |
|---|---|
| mib | 恢复的24位list，原位序 |
| sfn_lsb | 恢复的SFN低4位0..15，整数 |
| system_frame_number | mib[1:7]与sfn_lsb拼接的完整SFN0..1023；不保证与调用方NRCell帧号一致 |
| half_frame | 恢复的0/1半帧位 |
| extra_bits | 3位list；Lmax64为SSB索引高3位，其他为k_ssb高位及2个保留位 |
| crc_ok | 24位CRC检查bool；不代表MIB语义/无线调度有效 |

## 公式及变量

下列BCH-1为文档自编号，依据固定TS38.212 V15.2.0 §7.1及原表7.1.1-1/7.1.2-1：

$$
a_{G(j_i)}=b_i,\quad v=2a_{G(7)}+a_{G(8)},\quad
M=\begin{cases}26&L_{max}=64\\29&L_{max}\in\{4,8\}\end{cases},\quad
\widetilde a_{\mathcal S}=a_{\mathcal S}\oplus c(vM:vM+M-1).\tag{BCH-1}
$$

b为追加时序后的int8[32]，a为交织载荷int8[32]；G是原表32项排列，j_i为原文各类别计数器（SFN0..9、半帧10、额外位11..13、其他14..31）。S为参与加扰的索引集合，26/29项；c为以PCI初始化的Gold；v为0..3整数分段编号。所有变量无量纲比特/索引，不是时域相位。载荷Gold与物理PBCH Gold是两个不同阶段。

文档自编号BCH-2，依据同版本§7.1.3～5、§5.3.1/§5.4.1：

$$
m=[\widetilde a,CRC24C(\widetilde a)],\quad x=Polar_{56,512,I_{IL}=1}(m),\quad
f_i=x_{J(i\bmod512)},\quad0\le i<864.\tag{BCH-2}
$$

m为int8[56]，x为int8[512]，f为int8[864]；J为原表5.4.1.1-1子块排列，输入交织使用原表5.3.1.1-1；没有PC位/编码位交织。接收将对应重复LLR求和后还原512个母码软值。幅度与噪声标定不属于本类。

```python
from common.NRBCHCode import NRBCHCode
c=NRBCHCode(1007,l_max=8,ssb_index=7,half_frame=1,k_ssb=23)
b=[0,1]*12
o=c.decode(20*(1-2*c.encode(b,sfn_lsb=6)))
assert o['crc_ok'] and o['mib']==b and o['system_frame_number']==678
```

[真实MATLAB验证](../../documentation/validation/NRSSB_validation.md)包含nrBCH逐比特比较。无ASN.1 MIB字段打包、SCL、PBCH盲软合并或广播周期管理。

## 逐变量说明

以下变量对应本文已有公式或算法表达式；规范基线和章节沿用对应公式处的引用。每行只定义一个变量，同名符号只在该公式上下文有效。

| 变量 | 含义与用途 | 范围/约束 | 单位 | 维度/类型 |
|---|---|---|---|---|
| b | 追加时序字段后的载荷，交织输入 | 每点0/1 | bit | int8[32] |
| i | 原载荷位位置，遍历32位输入 | 0..31 | bit索引 | 整数标量 |
| G | 原表的32项排列，确定交织位置 | 0..31的一一排列 | bit索引 | int[32] |
| j_i | 第i位所属类别的交织计数器，选择G地址 | SFN0..9、半帧10、extra11..13、其他14..31 | 索引 | 每输入位整数 |
|  a | 交织后的载荷，供载荷加扰 | 每点0/1 | bit | int8[32] |
| v | 由两位明文SFN确定的Gold片段号 | 0..3 | 片段索引 | 整数标量 |
| M | 参与载荷加扰的比特数 | Lmax64取26，Lmax4/8取29 | bit数 | 整数标量 |
| L_max | 半帧候选SSB数，选择附加字段与加扰规则 | 4/8/64 | 块数 | 整数标量 |
| S | 参与载荷加扰的位置集合 | 32位中的26/29个指定位置 | bit索引 | int[M] |
| c | 以PCI初始化的Gold比特，异或载荷 | 每点0/1 | bit | 一维比特序列 |
|  tilde_a | 载荷加扰结果，送CRC与Polar | 每点0/1；明文位置保留原值 | bit | int8[32] |
| m | 加扰载荷加24位CRC的Polar信息输入 | 每点0/1 | bit | int8[56] |
| x | Polar母码，供子块交织与重复 | 每点0/1 | bit | int8[512] |
| f | 最终速率匹配输出，供物理PBCH加扰 | 每点0/1 | bit | int8[864] |
| J | 子块交织排列，选择512点母码位 | 0..511的一一排列 | bit索引 | int[512] |
| I_IL | Polar输入交织开关，决定信息位预排列 | 本BCH固定1，即开启 | 无量纲 | 布尔选择常量 |
