# NRDLSCHCode：单码块DL-SCH与有限缓冲速率匹配

[源码](NRDLSCHCode.py)。固定TS38.212 V15.2.0 §7.2.1～6、§5.2.2、§5.3.2、§5.4.2。CRC/BG/Z选择和LDPC算子与UL-SCH相同，因此继承NRULSCHCode的已验证数值实现；下行按§7.2.5使用I_LBRM=1，本类覆盖有限缓冲比特选择，不把上行全缓冲假设直接当作下行规则。

| 字段/属性 | 含义、范围、单位、示例 |
|---|---|
| n_bits | TB信息位数A，整数16..8424、8位对齐，实际须满足单码块容量，例256 |
| target_code_rate | MCS给定R，有限0.0001..0.95，用于BG选择，例0.5；不是A/G |
| output_length | G，整数1..1000000，必须是Qm整数倍，例4000 |
| modulation_order=2 | Qm为2/4/6/8，单层QPSK/16/64/256QAM |
| redundancy_version=0 | RV索引0..3，例2 |
| max_iterations=30 | LDPC最大迭代次数，整数1..1000 |
| n_ref=None | 已由上层确定的Nref，整数1..10000000；None明确使用Nref=N作为非限制性边界，不自动推导UE能力/TBS_LBRM |
| crc_length | A≤3824为16，其他24A，单位bit |
| base_graph | BG2：A≤292，或A≤3824且R≤0.67，或R≤0.25；其余BG1 |
| lifting_size | 原表允许的最小Z，满足Kb*Z≥A+CRC；整数2..384 |
| buffer_length | Ncb=min(N,Nref)，N为已打孔母码长度BG1的66Z或BG2的50Z |

构造/`__post_init__`先复用基类范围、字节对齐和单码块校验，再检查Nref。超出BG1含CRC8448/BG2含CRC3840的单码块容量明确拒绝，不静默丢失数据。

`ldpc()`返回NRLDPCCode实例。`crc(bits,length)`复用CRC16/24A（0x11021/0x1864cfb，含最高位，初态0无掩码），返回int8[length]，是内部辅助，不支持CRC24B。

`rate_indices()`返回int[G]，先在Ncb缓冲中从RV起点循环选择，跳过对应NULL填充位；不足时重复，所有索引0..Ncb-1。下式DLSCH-1是本文自编号，依据TS38.212 V15.2.0 §5.4.2.1、原表5.4.2.1-2及§7.2.5，不冒充原文公式编号：

$$
N_{\rm cb}=\min(N,N_{\rm ref}),\qquad
k_0=\left\lfloor\frac{a_{\rm RV}N_{\rm cb}}{N}\right\rfloor Z.\tag{DLSCH-1}
$$

| 变量 | 含义、范围、单位、维度 |
|---|---|
| N | 打孔后LDPC母码长度，确定循环缓冲上限；取值范围/约束：BG1为66Z，BG2为50Z；单位：bit；维度/类型：整数标量 |
| N_ref | 高层给定有限缓冲上限，限制本次可用编码位；取值范围/约束：None不限制或正整数，须满足类约束；单位：bit；维度/类型：整数标量/None |
| N_cb | 实际循环缓冲长度，限制速率匹配取位；取值范围/约束：N_cb=min(N,N_ref)，None时取N；单位：bit；维度/类型：整数标量 |
| Z | LDPC lifting大小，决定提升矩阵尺寸；取值范围/约束：R15支持集合中的整数2..384；单位：提升因子；维度/类型：整数标量 |
| RV | 冗余版本，选择循环缓冲读起点；取值范围/约束：整数0..3；单位：版本索引；维度/类型：整数标量 |
| k0 | 实际循环缓冲起始位，决定本RV输出位序；取值范围/约束：由BG/RV/N_cb/Z及规范起点式导出，0≤k0<N_cb；单位：bit索引；维度/类型：整数标量 |
| a_RV | BG1为[0,17,33,56]，BG2为[0,13,25,43]，原表系数，无量纲 |
| A | 原始传输块长度，决定CRC和码块配置；取值范围/约束：正整数，满足类支持的单码块范围；单位：bit；维度/类型：整数标量 |
| K | LDPC系统信息容量，决定填充长度；取值范围/约束：BG1为22Z，BG2为10Z；单位：bit；维度/类型：整数标量 |
| G | 速率匹配输出位数，适配本次数据RE容量；取值范围/约束：正整数且满足Qm分组；单位：bit；维度/类型：整数标量 |
| Qm | 每调制符号位数，用于调制位交织；取值范围/约束：QPSK2/16QAM4/64QAM6/256QAM8；单位：bit/符号；维度/类型：整数标量 |

`encode(bits)`：严格整数二进制[A]，拒绝bool。附加TB CRC，尾部NULL填充，调用共享LDPC编码和头2Z打孔，再通过本类有限缓冲索引及调制位交织输出int8[G]。`decode(llr)`：有限float[G]，正支持0；反交织后按相同有限缓冲索引软累加到完整母码，缓冲外未知位补零LLR而非已知0，再调用LDPC及TB CRC。

decode返回dict：bits为A位list（失败仍返回候选）；crc_ok严格bool，要求LDPC收敛且CRC一致；converged为LDPC校验状态；iterations为本次迭代次数。所有LLR/软分数无量纲，无校准噪声方差。错误类型/范围/形状由基类及本类抛校验异常；若有限缓冲无可选位则ValueError。

```python
from common import NRDLSCHCode
codec = NRDLSCHCode(256, .5, 4000, n_ref=1440)
bits = [0,1]*128
out = codec.decode(20*(1-2*codec.encode(bits)))
assert out['crc_ok'] and out['bits'] == bits
```

本类不实现多码块分段/CRC24B、HARQ软合并、MCS/TBS自动选择或从UE带宽/层数能力推导TBS_LBRM。调用方应按配置提供Nref；None相当于缓冲界至少等于N的特例，不宣称自动完成R15有限缓冲参数选择。某些RV单独、过少观测可能不收敛，无噪也不保证恢复，失败不能报成功。

当前PDSCH单码字支持1～4层。单码块的速率匹配总长度仍为G，资源类保证G可被Qm*n_layers整除；层映射在编码/加扰/QAM之后，不在本类执行。多码块按层分配E的流程仍未实现。

边界测试补充：对当前支持的字节对齐单码块TBS和BG/Z选择，2Z始终小于TB加CRC长度B，因此最小Nref=1仍保留可选信息位；不同RV的单元素缓冲均选择索引0。非法多码块仍按原边界拒绝，不增加范围外行为。详见test_NRDLSCHCode.py的最小缓冲及全TBS域约束测试。
