# NRPUCCH3Transmitter

[源码](NRPUCCH3Transmitter.py)。原始UCI→[NRUCICode](../common/NRUCICode.md)→[F3调制/DFT/DMRS](NRPUCCH3.md)→NRGrid→NROFDM。固定TS38.212 V15.2.0 §6.3.1及TS38.211 V15.2.0 §6.3.2.6、§6.4.1.3.3、§5.3.1。

| 字段 | 含义、范围、示例 |
|---|---|
| resource | NRPUCCH3，必须该类型 |
| carrier_frequency_hz=0 | 有限非负载频Hz，用于NR符号相位补偿，例3.5e9 |
| plot_config=None | 可选NRPlotConfig；None禁用，例NRPlotConfig(enabled=True) |

构造/`__post_init__`校验类型、载频及绘图配置。`transmit(bits,beta=1,*,plotter=None)`：bits为3..1706个整数二进制UCI，beta为非负线性幅度；含每块CRC后码率不得超过0.6，资源不足抛ValueError。plotter可传共享NRStagePlotter。使用标准规定的小块/Polar分支，不调用LDPC或经典RM替代NR小块码。

输出dict：waveform为complex[1,T]完整slot时域波形；grid为单端口NRGrid；coded_bits为int8[E]编码位；symbols为complex[S*M]未乘beta的DFT预编码数据、不含DMRS。T=cell.samples_per_slot，E=resource.coded_length，S/M见资源文档；复数均为归一化幅度。

绘图tx.coded_bits、tx.transform_precoded、tx.mapped_grid及OFDM内部阶段，禁用不导入Matplotlib；有独立plotter时非阻塞显示，共享时由调用方show。不保存图片。

```python
from cell import NRCell
from pucch import NRPUCCH3, NRPUCCH3Transmitter
r = NRPUCCH3(NRCell(n_size_grid=24), n_prbs=3)
out = NRPUCCH3Transmitter(r).transmit([0,1]*16)
```
