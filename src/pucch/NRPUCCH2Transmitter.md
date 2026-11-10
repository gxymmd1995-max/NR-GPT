# NRPUCCH2Transmitter

[源码](NRPUCCH2Transmitter.py)实现原始UCI→[公共UCI编码](../common/NRUCICode.md)→速率匹配→[加扰QPSK和DMRS](NRPUCCH2.md)→NRGrid→NROFDM。固定TS38.212 V15.2.0 §6.3.1及TS38.211 V15.2.0 §6.3.2.5/§6.4.1.3.2/§5.3.1。

| 字段 | 含义、范围、示例 |
|---|---|
| resource | 必须NRPUCCH2，例NRPUCCH2(NRCell(n_size_grid=12),n_prbs=3) |
| carrier_frequency_hz=0 | 有限非负载频Hz，例3.5e9，用于NR符号相位补偿 |
| plot_config=None | 可选NRPlotConfig，None关闭，例NRPlotConfig(enabled=True) |

自动构造/`__post_init__`校验资源、OFDM载频与绘图配置。`transmit(bits,beta=1,*,plotter=None)`：bits为3..1706整数位，beta非负线性幅度；plotter为可选共享NRStagePlotter。检查含CRC的码率≤0.6，不足要求增加PRB；A≤11使用小块码；A≥12使用CRC6/CRC11、Polar PC位、分段及完整速率匹配。原始HARQ/SR/CSI字段拼接与调度maxCodeRate选择不属于本类。

输出dict：waveform为complex[1,T]完整slot；grid为单端口NRGrid；coded_bits为int8[E]速率匹配编码位；symbols为complex[E/2]未乘beta的加扰QPSK数据（不含DMRS）。T=cell.samples_per_slot，E=resource.coded_length。复幅度均归一化，无绝对功率标定。

绘图tx.coded_bits、tx.qpsk、tx.mapped_grid以及OFDM所有阶段；独立调用自动非阻塞show，共享plotter由调用方show。禁用不导入绘图库，只显示不保存图片。

```python
from cell import NRCell
from pucch import NRPUCCH2, NRPUCCH2Transmitter
r = NRPUCCH2(NRCell(n_size_grid=12), n_prbs=3)
wave = NRPUCCH2Transmitter(r).transmit([1,0,1,1,0])['waveform']
```

当前公共接口：NRUCICode按A自动选择小块码或Polar，不调用LDPC或经典RM替代标准小块基矩阵。接收增加crc_ok：Polar为bool，小块/未检测为None；CRC失败仍返回判决位，detected只表示信号检测，不表示CRC通过。完整链路见NRPUCCH2_Polar_demo.py。

## 新手处理流程与资源图入口

F2承载编码UCI：NRUCICode按载荷长度选择小块码/Polar等对应流程，输出速率匹配位；再数据加扰、QPSK，与独立Gold QPSK DMRS一起映射。参考信号不承载UCI，接收端用它估计信道。输入位数、编码长度和分配资源必须匹配，不能仅修改n_bits而保留不足的资源。

[NRPUCCH2的时频位置、长度、配置变化及图例](NRPUCCH2.md)与[统一坐标/采样点换算](../../documentation/channel_walkthrough.md)提供完整阅读顺序。当前类的输入输出单位、形状及异常约束以上文字段/API节为准。
