# NRLDPCCode：NR QC-LDPC码块编解码

固定TS38.212 V15.2.0 §5.3.2、原表5.3.2-1/-2/-3。_coding_tables.json保留BG1的316个及BG2的197个非零块及8组移位值，直接提取固定版本规范，不引入第三方库实现。

字段：base_graph整数1/2；lifting_size为原表允许Z（2..384的51种离散值）；max_iterations默认30，正整数；normalization默认0.75，有限(0,1]，归一化最小和系数。例NRLDPCCode(2,16)。__post_init__校验类型/范围。n_bits属性为K=22Z/BG1或10Z/BG2；code_length属性为N=66Z/50Z（已打孔）。LIFTING_SETS模块常量为原表5.3.2-1的8组整数列表。

check_rows()返回完整H各行的变量索引数组list[int[]]，BG1有46Z行/68Z列，BG2有42Z行/52Z列。循环置换右移V%Z，即行t连接列(t+V)%Z；数组索引和位数无量纲，均零基。

encode(bits)输入整数[K]，0/1及填充标记-1；填充按0求校验，输出对应未打孔系统填充位置恢复-1。内部通过稀疏集合GF(2)消元解H*[信息;校验]=0；返回int8[N]，删除头2Z位。不是生产级编码器：大Z时消元耗时/内存显著，未提供吞吐承诺。调用方负责BG/Z选择、分段、CRC、填充布局和速率匹配。

decode(llr,filler_positions=())输入有限float[N]，正支持0；先补头2Z个零LLR（被打孔、未知），分层归一化最小和迭代。filler_positions是完整K域已知填充0的位置，范围0..K-1，例(100,101)，需由调用方提供。内部把LLR截到±1e4，填充约束置1e6。返回dict：bits为int8[K]（填充输出0），converged为bool校验是否通过，iterations为整数1..max_iterations。校验通过不等于CRC通过；未收敛仍返回当前硬判决。LLR无量纲、位置整数索引。

非法形状/非二进制/非有限输入抛ValueError；不可解/秩缺失抛RuntimeError。当前仅单码块，非完整传输块编解码，也不接受速率匹配后的E位流直接译码。

```python
from common import NRLDPCCode
c=NRLDPCCode(1,8)
b=[0,1]*(c.n_bits//2)
r=c.decode(20*(1-2*c.encode(b)))
assert r['converged'] and r['bits'].tolist()==b
```
