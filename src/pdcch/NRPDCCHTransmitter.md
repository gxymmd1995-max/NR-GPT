# NRPDCCHTransmitter

[源码](NRPDCCHTransmitter.py)。固定TS38.211 V15.2.0 §7.3.2/§7.4.1.3/§5.3.1及TS38.212 V15.2.0 §7.3.2～4。单候选单端口；DCI使用[NRDCICode](../common/NRDCICode.md)，接收SC算法为工程实现。

| 字段 | 含义、范围、单位、示例 |
|---|---|
| resource | NRPDCCH，显式时频候选 |
| rnti=1 | CRC掩码整数0..65535，例4321；与resource.scrambling_rnti分别配置 |
| carrier_frequency_hz=0 | 有限非负载频Hz，例3.5e9，用于NROFDM符号相位补偿 |
| plot_config=None | NRPlotConfig或None，例NRPlotConfig(enabled=True,channel="PDCCH")；只显示、不保存 |

构造/__post_init__验证资源、RNTI、OFDM和绘图配置。transmit(bits,beta=1,*,plotter=None)输入整数二进制[A]，A=12..140；A+24须不超过E，beta有限非负线性幅度、无量纲；plotter为可选共享NRStagePlotter。执行CRC24C/RNTI→Polar/速率匹配→加扰/QPSK/DMRS→NRGrid→完整slot NROFDM。

输出dict：waveform为complex[1,T]（T=cell.samples_per_slot）；grid为单端口NRGrid；coded_bits为int8[E]；symbols为未乘beta的complex[54L]。物理Tx映射/多Rx信道由调用方提供。阶段tx.coded_bits、tx.qpsk、tx.mapped_grid及OFDM各步骤；独立调用show，共享plotter由调用方show。

```python
from cell import NRCell
from pdcch import NRPDCCH,NRPDCCHTransmitter,NRPDCCHReceiver
r=NRPDCCH(NRCell())
sent=NRPDCCHTransmitter(r).transmit([0,1]*16)
out=NRPDCCHReceiver(r,32).receive(sent["waveform"])
assert out["crc_ok"] and out["bits"]==[0,1]*16
```

详见[独立MATLAB验证](../../documentation/validation/NRPDCCH_validation.md)。

## 新手处理流程与资源图入口

DCI比特经CRC24C/RNTI掩码、Polar和速率匹配、加扰、QPSK后映射到所选CCE候选，另生成DMRS。CRC掩码RNTI和物理数据加扰RNTI是分别配置的用途，不应混成一个自动推断参数。

[NRPDCCH的时频位置、长度、配置变化及图例](NRPDCCH.md)与[统一坐标/采样点换算](../../documentation/channel_walkthrough.md)提供完整阅读顺序。当前类的输入输出单位、形状及异常约束以上文字段/API节为准。
