# NRPDCCHReceiver

[源码](NRPDCCHReceiver.py)。固定TS38.211 V15.2.0 §7.3.2/§7.4.1.3/§5.3.1及TS38.212 V15.2.0 §7.3.2～4。单候选单端口；DCI使用[NRDCICode](../common/NRDCICode.md)，接收SC算法为工程实现。

| 字段 | 含义、范围、单位、示例 |
|---|---|
| resource | NRPDCCH，显式时频候选 |
| rnti=1 | CRC掩码整数0..65535，例4321；与resource.scrambling_rnti分别配置 |
| carrier_frequency_hz=0 | 有限非负载频Hz，例3.5e9，用于NROFDM符号相位补偿 |
| plot_config=None | NRPlotConfig或None，例NRPlotConfig(enabled=True,channel="PDCCH")；只显示、不保存 |
| n_bits | DCI位数12..140，与发送一致，例32 |
| detection_threshold=.1 | DMRS归一化相关能量比门限0..1，严格大于才检测；非dB |

构造/__post_init__验证配置。receive(waveform,*,known_frequency_offset_hz=0,known_initial_phase_rad=0,known_delay_samples=0,cp_fraction=1,plotter=None)输入有限complex[Rx,T]，Rx=cell.n_rx_antennas、T=cell.samples_per_slot。已知频偏Hz、初相rad先反旋，整数样点净延迟提前补偿；cp_fraction为0..1的CP内FFT窗比例；plotter可选共享NRStagePlotter。

每REG以3个DMRS做LS估计h=mean(y*conj(reference))，假设该REG内平坦；跨Rx做MRC，取实部/虚部软值、解扰及DCI SC/CRC。该接收公式为文档自编号PDCCH-RX-1：h为complex[Rx,6L]，分子sum_Rx(conj(h)*data)为complex[6L,9]，权重sum_Rx(abs(h)^2)为float[6L]；除权重得到均衡QPSK。DMRS能量比clip至0..1，零能量检测失败。固定3/9点源于上述规范RE映射；LS/MRC是项目算法，无绝对噪声估计或CFAR。

返回dict：detected为bool；bits为A位list或未检测时None；crc_ok为bool或未检测时None；metric为0..1分数；soft_bits为float[E]正支持0；equalized_symbols为complex[6L,9]；channel_estimates为complex[Rx,6L]含发送beta；rx_grid为complex[Rx,slot符号数,载波子载波数]。CRC失败仍返回候选位，不仅凭detected判断成功。

绘图rx.channel_estimates、rx.equalized_constellation、rx.soft_bits以及OFDM步骤；只显示不保存。不含盲同步、盲候选/长度/RNTI搜索、时频插值、SCL或DCI语义解析。

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

OFDM解调后按所选候选提取REG。每REG用3个DMRS做平坦LS估计，对9个数据点跨Rx进行MRC，形成QPSK软值并解扰，再Polar SC译码、检查RNTI掩码CRC。当前需要知道候选位置、DCI长度和CRC RNTI；不是同时搜索全部长度/RNTI的盲解码器。

[NRPDCCH的时频位置、长度、配置变化及图例](NRPDCCH.md)与[统一坐标/采样点换算](../../documentation/channel_walkthrough.md)提供完整阅读顺序。当前类的输入输出单位、形状及异常约束以上文字段/API节为准。
