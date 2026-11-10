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

## 新手处理流程与资源图入口

F3先UCI编码/速率匹配，再加扰，选择QPSK或π/2-BPSK；每个数据符号做12×n_prbs点单位化DFT预编码，再映射连续频率资源。这里的DFT预编码和之后的载波IFFT是两个不同操作，接收端必须在均衡后做IDFT恢复调制符号。

[NRPUCCH3的时频位置、长度、配置变化及图例](NRPUCCH3.md)与[统一坐标/采样点换算](../../documentation/channel_walkthrough.md)提供完整阅读顺序。当前类的输入输出单位、形状及异常约束以上文字段/API节为准。
