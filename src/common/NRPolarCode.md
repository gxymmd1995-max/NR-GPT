# NRPolarCode：Polar母码编码与SC译码

固定TS38.212 V15.2.0 §5.3.1、原表5.3.1.1-1及5.3.1.2-1。源码同目录同名。_coding_tables.json的可靠度序列/输入交织表直接从固定R15原文提取，非第三方算法代码。

字段：n_bits为K，整数1..N；code_length为N，只能32/64/128/256/512/1024；input_interleaving默认False，严格bool，开启时K≤164。示例NRPolarCode(32,64)。冻结dataclass；__post_init__拒绝非法范围/类型。

information_indices()返回排序后的信息位索引int[K]，选择N内可靠度最高K位；permutation()返回输入交织索引int[K]，关闭时恒等。encode(bits)接收整数二进制[K]，拒绝bool，返回int8[N]母码。算法为GF(2)蝶形变换u*G_N，G_N由[[1,0],[1,1]]的Kronecker幂得到；输入位先交织并放置信息位置，其余冻结为0。符号K/N是位数，无量纲；u/x是二进制[N]；索引0..N-1。依据上述规范章节，此处表达为推导说明，不引入伪规范编号。

decode(llr)接收有限float[N]，正支持0，负支持1；SC递归f=min-sum近似、g=b+(1-2*u)*a，冻结位置强制0，恢复交织前int8[K]信息位。LLR无量纲，未提供CRC通过标志。非法形状/值抛ValueError。

边界：这是指定N、零PC位母码核；不包含CRC、SCL、PC辅助位、E驱动码长选择、打孔/缩短或速率匹配/恢复。完整NR UCI的CRC、PC位和速率匹配由NRUCICode组合实现，PUCCH F2已通过该类支持长UCI；本母码类不独立承担整条链。SC性能不等同Toolbox的SCL。

```python
from common import NRPolarCode
c=NRPolarCode(32,64)
b=[0,1]*16
assert c.decode(20*(1-2*c.encode(b))).tolist()==b
```

新增transform(bits)静态蝶形接口，返回相同长度int8母码，用于NRUCICode已配置冻结/PC位的向量。完整UCI的CRC/PC/速率匹配在[NRUCICode](NRUCICode.md)，不改变本类原有母码接口。

## 逐变量说明

以下变量对应本文已有公式或算法表达式；规范基线和章节沿用对应公式处的引用。每行只定义一个变量，同名符号只在该公式上下文有效。

| 变量 | 含义与用途 | 范围/约束 | 单位 | 维度/类型 |
|---|---|---|---|---|
| K | Polar信息位数，决定信息集合大小 | 1..N；开启输入交织时还须K≤164 | bit数 | 整数标量 |
| N | Polar母码长度，决定蝶形规模 | 32/64/128/256/512/1024 | bit数 | 整数标量 |
| u | 填入信息与冻结位后的母码输入 | 每点0/1，冻结为0 | bit | int8[N] |
| x | GF(2)变换后的母码输出 | 每点0/1 | bit | int8[N] |
| G_N | Polar生成变换，计算uG_N | 由[[1,0],[1,1]]的log2N次Kronecker幂得到 | 无量纲 | 概念int[N,N] |
| a | SC的一个输入LLR，用于f/g递归 | 有限实数，正支持0 | 无量纲软值 | 标量或等长子数组 |
| b | SC的另一个输入LLR，与a组合 | 有限实数，正支持0 | 无量纲软值 | 与a同形 |
| u_hat | g更新中的已判左侧比特，决定LLR正负 | 0/1；文中g式简记为u，不是整条母码 | bit | 标量或子数组 |
