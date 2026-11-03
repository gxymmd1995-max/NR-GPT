# NRPUCCH1Transmitter

[源码](NRPUCCH1Transmitter.py)将[NRPUCCH1](NRPUCCH1.md)的数据/DMRS映射到NRGrid，再调用NROFDM生成当前slot时域信号。规范依据TS38.211 V15.2.0 §6.3.2.4、§6.4.1.3.1、§5.3.1。单逻辑端口，物理天线由信道模块映射。

| 字段 | 含义/范围/示例 |
|---|---|
| resource | 必须NRPUCCH1，例NRPUCCH1(NRCell()) |
| carrier_frequency_hz=0 | 有限非负载频Hz，例3.5e9；用于NR符号相位补偿 |
| plot_config=None | NRPlotConfig或None，None关闭；例NRPlotConfig(enabled=True) |

自动构造及`__post_init__`校验资源类型、OFDM载频、绘图配置。`transmit(bits,beta=1,*,plotter=None)`输入1/2整数位、非负线性幅度beta，以及可选共享NRStagePlotter。输出字典：waveform为complex[1,T]完整slot样点；grid为单端口NRGrid；symbols为complex[L,12]未乘beta参考/数据；indices为int[12L,3]。T是cell.samples_per_slot，L是资源符号数；复数均为归一化幅度，坐标详见资源类。

绘图阶段tx.reference显示带OCC参考，tx.mapped_grid显示数据/DMRS网格，OFDM内部继续显示相位补偿、IFFT和CP阶段。共享plotter由调用方show；独立使用时非阻塞show。只显示、不保存图片。禁用不导入Matplotlib。

```python
from cell import NRCell
from pucch import NRPUCCH1, NRPUCCH1Transmitter
tx = NRPUCCH1Transmitter(NRPUCCH1(NRCell(n_size_grid=6)))
result = tx.transmit([0, 1], beta=0.8)
```
