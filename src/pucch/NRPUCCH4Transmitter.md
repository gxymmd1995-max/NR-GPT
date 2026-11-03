# NRPUCCH4Transmitter

[源码](NRPUCCH4Transmitter.py)。原始UCI→NRUCICode小块/Polar编码→数据加扰/调制→OCC扩频→12点DFT→NRGrid及DMRS→NROFDM时域波形。固定TS38.212 V15.2.0 §6.3.1及TS38.211 V15.2.0 §6.3.2.6、§6.4.1.3.3、§5.3.1。

| 字段 | 含义、范围、示例 |
|---|---|
| resource | 必须NRPUCCH4，包含SF、OCC及当前slot配置 |
| carrier_frequency_hz=0 | 有限非负载频Hz，例3.5e9，用于NR符号相位补偿 |
| plot_config=None | 可选NRPlotConfig，None禁用，例NRPlotConfig(enabled=True) |

构造/`__post_init__`校验资源、载频与绘图配置。`transmit(bits,beta=1,*,plotter=None)`输入整数二进制UCI（公共接口3..1706位，实际受单RB容量限制）、非负线性幅度beta、可选共享NRStagePlotter。含CRC的码率不得超过0.6，超出抛ValueError，不能通过省略编码或CRC绕过。

输出dict：waveform为complex[1,T]完整slot波形；grid为单端口NRGrid；coded_bits为int8[E]；symbols为complex[12S]未乘beta的DFT预编码数据，不含DMRS。T=cell.samples_per_slot；S为数据符号数，E见[资源文档](NRPUCCH4.md)，复幅度均归一化。

绘图tx.coded_bits、tx.occ、tx.transform_precoded、tx.mapped_grid及OFDM内部阶段。独立调用非阻塞show，共享plotter由调用方show。禁用不导入Matplotlib；图像只显示，不保存。

```python
from cell import NRCell
from pucch import NRPUCCH4, NRPUCCH4Transmitter
r = NRPUCCH4(NRCell(n_size_grid=6), spreading_factor=2, occ_index=1)
sent = NRPUCCH4Transmitter(r).transmit([0,1]*16)
```
