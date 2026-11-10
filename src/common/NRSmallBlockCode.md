# NRSmallBlockCode：3～11位UCI编码/软译码

[源码](NRSmallBlockCode.py)。无状态工具类，无字段、缓存或可变配置；仅静态方法。固定TS38.212 V15.2.0 §5.3.3.3、§5.4.3、§6.3.1.2～4。[_small_block_tables.py](_small_block_tables.py)为原表5.3.3.3-1的32行11列，不是MATLAB参考数据。适用于PUCCH F2/3/4的小块编码，不实现1/2位特殊编码，也不实现12位以上Polar/CRC。

`encode(bits,output_length)`：bits为3..11个整数0/1，拒绝bool；output_length为整数K..8192。返回int8[E]编码位，先按原表生成32位母码，再按索引mod32截取/重复。不验证调度码率或资源适用性，调用方必须分配足够E，过短截取可能导致码字不可区分。

`decode(llr,n_bits)`：llr为有限一维实数组，长度E介于n_bits..8192，正数支持比特0，负数支持比特1；n_bits为整数3..11。先将重复位置软值相加，再遍历2^K个码字做最大相关，返回K个整数位list。相等分数选数值索引最小的候选（候选位序为低位先）；零软输入不表示有效检测，DTX由外层判定。无CRC通过标志。异常输入抛ValueError或整数类型校验异常。

文档自编号SB-1，推导依据上述固定版本章节与原表：

$$
d_i=\left(\sum_{k=0}^{K-1}M_{i,k}b_k\right)\bmod2,\quad f_j=d_{j\bmod32}.\tag{SB-1}
$$

| 变量 | 含义、范围、单位、维度 |
|---|---|
| K | 原始信息位数量，选择基矩阵参与行数；取值范围/约束：整数3..11；单位：bit；维度/类型：整数标量 |
| E | 速率匹配输出长度，选择重复/截取位数；取值范围/约束：整数K..8192；单位：bit；维度/类型：整数标量 |
| i | 32位母码的点索引，选择基矩阵列；取值范围/约束：0..31；单位：bit索引；维度/类型：整数标量 |
| k | 输入信息位索引，选择基矩阵行；取值范围/约束：0..K−1；单位：bit索引；维度/类型：整数标量 |
| j | 输出速率匹配位索引，循环读取母码；取值范围/约束：0..E−1；单位：bit索引；维度/类型：整数标量 |
| M | 原表二进制基矩阵，int[32,11] |
| b | 原始信息位，决定基矩阵线性组合；范围：每点0/1；单位：bit；维度：int[K] |
| d | 32位母码，供速率匹配循环读取；范围：每点0/1；单位：bit；维度：int[32] |
| f | 速率匹配输出，供物理调制；范围：每点0/1；单位：bit；维度：int[E] |
| llr | 无量纲软可靠性，float[E]；等比例缩放不改变ML判决 |

```python
from common.NRSmallBlockCode import NRSmallBlockCode
word = NRSmallBlockCode.encode([1,0,1], 48)
assert NRSmallBlockCode.decode((1-2*word).astype(float), 3) == [1,0,1]
```
