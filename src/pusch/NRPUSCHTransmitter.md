# NRPUSCHTransmitter

[源码](NRPUSCHTransmitter.py)。TB原始位→NRULSCHCode CRC/LDPC/速率匹配→NRPUSCH加扰/QAM/DMRS→NRGrid→NROFDM完整slot。固定TS38.212 V15.2.0 §6.2及TS38.211 V15.2.0 §6.3.1/§6.4.1.1/§5.3.1。

| 字段 | 含义、范围、示例 |
|---|---|
| resource | 必须NRPUSCH，单层资源 |
| target_code_rate=.5 | 有限0.0001..0.95，MCS给定目标值，用于BG选择 |
| redundancy_version=0 | RV整数0..3 |
| carrier_frequency_hz=0 | 有限非负载频Hz，例3.5e9，用于NR符号相位补偿 |
| plot_config=None | 可选NRPlotConfig，None禁用；例NRPlotConfig(enabled=True,channel='PUSCH') |

构造/`__post_init__`校验类型和共享编码/OFDM配置。`transmit(bits,beta=1,*,plotter=None)`要求整数二进制TB[A]，A字节对齐、符合单LDPC码块限制；beta非负线性幅度；plotter可传共享NRStagePlotter。保护检查(A+CRC)/G≤0.95，不代替标准MCS/TBS调度选择。错误输入/资源不足明确抛异常。

输出dict：waveform为complex[1,T]完整slot；grid为单端口NRGrid；coded_bits为int8[G]；base_graph为1/2；lifting_size为Z整数。T=cell.samples_per_slot，G=resource.coded_length，复幅度均归一化，无绝对瓦特标定。

绘图tx.coded_bits、tx.modulation、tx.grid和OFDM内部相位/FFT/IFFT/CP步骤。独立调用非阻塞show，共享plotter由调用方show；禁用不导入绘图库，图像只显示不保存。

```python
from cell import NRCell
from pusch import NRPUSCH, NRPUSCHTransmitter
r = NRPUSCH(NRCell(n_size_grid=12), n_symbols=12)
sent = NRPUSCHTransmitter(r).transmit([0,1]*128)
```
