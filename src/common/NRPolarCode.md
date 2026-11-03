# NRPolarCode：Polar母码编码与SC译码

固定TS38.212 V15.2.0 §5.3.1、原表5.3.1.1-1及5.3.1.2-1。源码同目录同名。_coding_tables.json的可靠度序列/输入交织表直接从固定R15原文提取，非第三方算法代码。

字段：n_bits为K，整数1..N；code_length为N，只能32/64/128/256/512/1024；input_interleaving默认False，严格bool，开启时K≤164。示例NRPolarCode(32,64)。冻结dataclass；__post_init__拒绝非法范围/类型。

information_indices()返回排序后的信息位索引int[K]，选择N内可靠度最高K位；permutation()返回输入交织索引int[K]，关闭时恒等。encode(bits)接收整数二进制[K]，拒绝bool，返回int8[N]母码。算法为GF(2)蝶形变换u*G_N，G_N由[[1,0],[1,1]]的Kronecker幂得到；输入位先交织并放置信息位置，其余冻结为0。符号K/N是位数，无量纲；u/x是二进制[N]；索引0..N-1。依据上述规范章节，此处表达为推导说明，不引入伪规范编号。

decode(llr)接收有限float[N]，正支持0，负支持1；SC递归f=min-sum近似、g=b+(1-2*u)*a，冻结位置强制0，恢复交织前int8[K]信息位。LLR无量纲，未提供CRC通过标志。非法形状/值抛ValueError。

边界：这是指定N、零PC位母码核；不包含CRC、SCL、PC辅助位、E驱动码长选择、打孔/缩短或速率匹配/恢复。因此尚不能代替完整NR UCI Polar链，F2的12位以上限制仍保留。SC性能不等同Toolbox的SCL。

```python
from common import NRPolarCode
c=NRPolarCode(32,64)
b=[0,1]*16
assert c.decode(20*(1-2*c.encode(b))).tolist()==b
```

新增transform(bits)静态蝶形接口，返回相同长度int8母码，用于NRUCICode已配置冻结/PC位的向量。完整UCI的CRC/PC/速率匹配在[NRUCICode](NRUCICode.md)，不改变本类原有母码接口。
