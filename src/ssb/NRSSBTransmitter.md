# NRSSBTransmitter：SS/PBCH块时域发射

[源码](NRSSBTransmitter.py)。固定TS38.212 V15.2.0 §7.1及TS38.211 V15.2.0 §7.4.2/§7.4.3/§5.3.1。链路：24位BCH输入+SFN低位→载荷交织/加扰/CRC/Polar→PSS/SSS/PBCH/DMRS→NRGrid→完整slot OFDM。

| 字段 | 含义、范围、单位、示例 |
|---|---|
| resource | 必须NRSSB，例NRSSB(NRCell(n_size_grid=24)) |
| carrier_frequency_hz=0 | 有限非负载频Hz，例3.5e9；用于NROFDM相位补偿 |
| plot_config=None | NRPlotConfig或None；例NRPlotConfig(enabled=True,channel='SSB')，None关闭 |

构造/__post_init__检查资源、OFDM及绘图配置。transmit(mib,sfn_lsb=0,beta=1,*,plotter=None)输入整数二进制MIB原始24位、SFN低4位0..15、有限非负线性幅度beta及可选共享NRStagePlotter。输入语义/时频关联由调用方保证，非法数值或形状明确拒绝。

输出dict：waveform为complex[1,T]，T=cell.samples_per_slot；grid为单端口NRGrid；coded_bits为int8[864]，未做物理加扰的BCH输出。一个逻辑端口对应一条波形，多Rx及物理天线映射在外部信道完成。幅度归一化，无dBm/瓦特标定。

绘图tx.pss、tx.sss、tx.bch_bits、tx.pbch、tx.grid，以及NROFDM相位/IFFT/CP各步骤；禁用不导入Matplotlib。独立调用结束show，共享plotter由调用方show，图片仅显示、不保存。数值公式和变量范围见[资源类](NRSSB.md)及[公共BCH](../common/NRBCHCode.md)。

```python
from cell import NRCell
from ssb import NRSSB,NRSSBTransmitter
r=NRSSB(NRCell(n_size_grid=24),start_subcarrier=24)
sent=NRSSBTransmitter(r).transmit([0,1]*12,sfn_lsb=6)
assert sent['waveform'].shape==(1,r.cell.samples_per_slot)
```

不负责MIB ASN.1、SSB突发集/Case A～E时机选择、CORESET0或载波/SSB不同间隔重采样。

## 新手处理流程与资源图入口

SSB组合PSS、SSS、PBCH及PBCH DMRS。PSS/SSS是127点同步序列；原始24位BCH输入加时序字段后载荷交织/加扰、CRC24C、Polar和速率匹配得到864位，再物理加扰及QPSK形成432个PBCH复数。两层加扰用途不同。

[NRSSB的时频位置、长度、配置变化及图例](NRSSB.md)与[统一坐标/采样点换算](../../documentation/channel_walkthrough.md)提供完整阅读顺序。当前类的输入输出单位、形状及异常约束以上文字段/API节为准。
