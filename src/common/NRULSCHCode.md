# NRULSCHCode：单码块UL-SCH传输块编码/译码

[源码](NRULSCHCode.py)。固定TS38.212 V15.2.0 §6.2.1～6、§5.2.2、§5.3.2、§5.4.2。复用NRLDPCCode，完成TB CRC、BG/Z选择、尾部NULL填充、LDPC、首2Z打孔、全缓冲区RV比特选择及调制位交织；接收反交织、重复软累加、填充约束、LDPC及CRC检查。只支持单码块，不处理多码块分段/CRC24B、有限缓冲LBRM或HARQ软合并。

| 字段/属性 | 含义、范围、单位与示例 |
|---|---|
| n_bits | 传输块A，整数16..8424，必须8位对齐；实际受单码块BG容量限制；例256 |
| target_code_rate | MCS给定的目标码率R，有限0.0001..0.95，例0.5；用于BG选择，不等于A/G |
| output_length | G，速率匹配输出位数，整数1..1000000且为Qm整数倍 |
| modulation_order=2 | Qm为2/4/6/8，单层对应QPSK/16/64/256QAM |
| redundancy_version=0 | RV索引整数0..3，例2 |
| max_iterations=30 | LDPC最大迭代次数，整数1..1000 |
| crc_length | TB CRC长度：A≤3824为16，否则24A |
| base_graph | BG2：A≤292，或A≤3824且R≤0.67，或R≤0.25；其他BG1 |
| lifting_size | 按原表离散集合选择最小满足Kb*Z≥A+CRC的Z，整数2..384 |

构造及`__post_init__`校验字段；单码块最大含CRC长度BG1=8448、BG2=3840，超过明确抛ValueError，不静默截断。BG1 Kb=22；BG2根据B=A+CRC选择Kb=10/9/8/6（B>640/>560/>192/其他），最终LDPC系统位容量仍为10Z。

`ldpc()`返回对应NRLDPCCode实例。`crc(bits,length)`是内部CRC16/24A辅助，返回int8[length]余数：初态0、无掩码，多项式分别0x11021、0x1864cfb（含最高位）；不用于CRC24B。`rate_indices()`返回int[G]，索引位于已打孔LDPC码字0..N-1；RV起点按原表5.4.2.1-2：BG1=[0,17,33,56]*Z，BG2=[0,13,25,43]*Z（全缓冲），跳过NULL，循环重复直到G位。

`encode(bits)`要求严格整数二进制[A]（不接受bool）。CRC后到LDPC容量K的尾部填-1，LDPC编码及打孔后用rate_indices选择；按Qm进行位交织，输出int8[G]。

`decode(llr)`要求有限float[G]，正值支持0。反位交织后按rate_indices累加到长度N的全缓冲观测（本次接收，不跨调用合并），用已知尾部填充位置调用LDPC译码。返回dict：bits为A位整数list（即使失败仍返回当前候选），crc_ok严格bool，必须LDPC收敛且TB CRC通过才True；converged为bool校验综合状态，iterations为本次迭代次数。未收敛的全零候选可能代数CRC为零，不能因此报成功。

ULSCH-1为文档自编号，依据TS38.212 V15.2.0 §5.4.2.2：

$$
f_{Q_mj+i}=e_{iG/Q_m+j},\qquad i=0,\ldots,Q_m-1,\quad j=0,\ldots,G/Q_m-1.\tag{ULSCH-1}
$$

| 变量 | 含义、范围、单位、维度 |
|---|---|
| A | 原始上行传输块信息位数；取值范围/约束：正整数，满足类单码块范围；单位：bit；维度/类型：整数标量 |
| B | 附加TB CRC后的长度；取值范围/约束：A+CRC长度；单位：bit；维度/类型：整数标量 |
| K | LDPC系统信息容量，决定填充位数量；取值范围/约束：BG1为22Z，BG2为10Z；单位：bit；维度/类型：整数标量 |
| N | 打孔后母码长度，用于速率匹配循环缓冲；取值范围/约束：BG1为66Z，BG2为50Z；单位：bit；维度/类型：整数标量 |
| G | 本次编码输出长度，匹配PUSCH数据资源；取值范围/约束：正整数，须满足调制分组约束；单位：bit；维度/类型：整数标量 |
| Z | LDPC lifting大小，决定编码矩阵提升尺寸；取值范围/约束：R15提升集合中的整数2..384；单位：提升因子；维度/类型：整数标量 |
| Q_m | 每个QAM符号携带的编码位数，用于交织；取值范围/约束：2/4/6/8对应QPSK到256QAM；单位：bit/符号；维度/类型：整数标量 |
| e | 位选择后的编码比特，作为调制位交织输入；取值范围/约束：每点0或1；单位：bit；维度/类型：int8[G] |
| f | 调制位交织后的编码比特，传给物理加扰；取值范围/约束：每点0或1；单位：bit；维度/类型：int8[G] |
| i | 调制符号组序号，遍历输出的Qm位组；取值范围/约束：0..G/Q_m−1；单位：组索引；维度/类型：整数标量 |
| j | 组内比特位置，选择交织对应的位；取值范围/约束：0..Q_m−1；单位：bit索引；维度/类型：整数标量 |
| llr | 无量纲float[G]，正支持0，缩放不等于绝对噪声标定 |

```python
from common import NRULSCHCode
codec = NRULSCHCode(256, .5, 4000, 2, 0)
bits = [0, 1]*128
out = codec.decode(20*(1-2*codec.encode(bits)))
assert out['crc_ok'] and out['bits'] == bits
```

TBS和目标码率由调用方给定，本类不执行MCS/TBS量化、不验证给定资源与TBS是否可由某个MCS调度过程共同得到。某些RV在单独、有限观测下不能恢复系统位，即使无噪也可能不收敛；增大迭代次数不保证成功，通常需足够观测或HARQ合并。本类不会伪造成功。大Z的稀疏GF(2)编码成本较高，不承诺实时吞吐。
