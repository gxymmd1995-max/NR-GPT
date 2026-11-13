# NR Release 15 物理层学习路线

第一遍按下表顺序学习，预计 8～10 小时。每站先读类文档的“新手导读”，再运行一个示例，对照资源网格和接收结果。遇到公式时查变量的单位、维度和取值范围，第二遍再读对应协议小节。[坐标与链路入门](channel_walkthrough.md) · [公式变量指南](formula_reference.md)

完成单个示例后，可以按主题做配置对照。每组同时画出资源网格和发射波形，适合观察增加符号数、切换 PCI 或改变参考密度时资源如何移动。[各信道与参考信号的对照练习](../examples/common/README.md#各信道和参考信号的配置对照)

## 第一遍阅读与实操清单

| 顺序 | 主题 | 按顺序阅读 | 动手练习和验收 |
|---|---|---|---|
| 1 · 60 分钟 | 公共基础 | [新手指南](channel_walkthrough.md) → [NRCell](../src/cell/NRCell.md) → [NRGrid](../src/grid/NRGrid.md) → [NROFDM](../src/common/NROFDM.md) → [NRChannel](../src/channel/NRChannel.md) | 运行 [NRCell](../examples/cell/NRCell_demo.py)、[OFDM](../examples/common/NROFDM_demo.py)。能把 BWP 内 PRB 换成载波局部子载波，并从 FFT、CP 和采样率算出一个符号的长度。分清样点时延、CFO 与 SNR 各自改变什么。 |
| 2 · 60 分钟 | SSB / PBCH | [SSB 资源](../src/ssb/NRSSB.md) → [SSB 接收机](../src/ssb/NRSSBReceiver.md) | 运行 [SSB 示例](../examples/ssb/NRSSB_demo.py)。在 240 子载波 × 4 符号内找出 PSS、SSS、PBCH 和 PBCH DM-RS，核对接收机输出的 PCI、SSB 索引、广播载荷和 CRC。 |
| 3 · 60 分钟 | PDCCH | [PDCCH 资源](../src/pdcch/NRPDCCH.md) → [DCI 编码](../src/common/NRDCICode.md) → [PDCCH 接收机](../src/pdcch/NRPDCCHReceiver.md) | 运行 [PDCCH 示例](../examples/pdcch/NRPDCCH_demo.py)。画出 CORESET、REG、CCE 和候选的关系，沿着 DCI、Polar、QPSK 到接收 CRC 走一遍。 |
| 4 · 100 分钟 | PDSCH → PUSCH | [PDSCH 资源](../src/pdsch/NRPDSCH.md) → [DL-SCH 编码](../src/common/NRDLSCHCode.md) → [PUSCH 资源](../src/pusch/NRPUSCH.md) → [UL-SCH 编码](../src/common/NRULSCHCode.md) | 先跑 [PDSCH](../examples/pdsch/NRPDSCH_demo.py)，再跑 [PUSCH](../examples/pusch/NRPUSCH_demo.py)。沿着 TB、CRC、LDPC、速率匹配、加扰、QAM 和数据 RE 追踪一次发射，指出接收端在哪一步用 DM-RS 估计信道、均衡和译码。 |
| 5 · 80 分钟 | PUCCH F0 → F1 → F2 → F3 → F4 | [F0](../src/pucch/NRPUCCH0.md) → [F1](../src/pucch/NRPUCCH1.md) → [F2](../src/pucch/NRPUCCH2.md) → [F3](../src/pucch/NRPUCCH3.md) → [F4](../src/pucch/NRPUCCH4.md) | 先跑 [F0 多用户](../examples/pucch/NRPUCCH0_multiuser_demo.py)，观察候选相关峰及 DTX，再用[符号数对照](../examples/pucch/NRPUCCH_symbol_counts_demo.py)比较 F0～F4 的时长和 DM-RS 位置。能说明 F0 的循环移位、F1 的时域 OCC、F2 的短时频资源、F3 的变换预编码和 F4 的单 RB OCC 各在什么阶段起作用。 |
| 6 · 60 分钟 | PRACH | [PRACH 资源](../src/prach/NRPRACH.md) → [PRACH 接收机](../src/prach/NRPRACHReceiver.md) | 先运行[长短格式时域对照](../examples/prach/NRPRACH_formats_demo.py)，比较 CP 和重复周期，再用 [PRACH 三 UE 示例](../examples/prach/NRPRACH_demo.py)核对不同循环移位的前导号和样点时延。 |
| 7 · 80 分钟 | SRS → CSI-RS → PT-RS | [SRS](../src/srs/NRSRS.md) → [SRS 接收机](../src/srs/NRSRSReceiver.md) → [CSI-RS](../src/csirs/NRCSIRS.md) → [上行 PT-RS](../src/ptrs/NRUplinkPTRS.md) → [下行 PT-RS](../src/ptrs/NRDownlinkPTRS.md) | 运行 [SRS 接收](../examples/srs/NRSRSReceiver_demo.py)、[CSI-RS 测量](../examples/csirs/NRCSIRS_demo.py)、[上下行 PT-RS](../examples/ptrs/README.md)。分别指出上行探测、下行测量和公共相位跟踪用哪些参考点，读懂 SRS 时延、SNR、RSRP 和上行 RI/TPMI，观察 PT-RS 如何插值补偿没有参考点的数据符号。 |

只有两小时的话，按第 1、2、3、4、5、6、7 站各取一篇首读文档，依次用 20、15、15、20、20、15、15 分钟，重点看资源图和接收输出。先跑 OFDM 和 PUCCH F0 两个示例，其他练习留到完整路线。

## 把信道放回通信流程

| 场景 | 沿哪条路径复习 | 自测问题 |
|---|---|---|
| 小区搜索与广播 | SSB 内的 PSS / SSS → PBCH → Type0-PDCCH / PDSCH | PCI 从哪里来？PBCH 携带的广播信息与后续 PDSCH 上的系统信息分别在哪里接收？ |
| 下行数据与反馈 | PDCCH 携带调度 DCI → PDSCH 携带下行数据 → PUCCH 或 PUSCH 承载 HARQ-ACK | DCI、TB 和 HARQ-ACK 分别经过哪条编码链？ |
| 上行调度与数据 | PUCCH 可承载 SR → PDCCH 可下发 UL grant → PUSCH 携带上行数据 | SR 与 UL grant 由谁发给谁？PUSCH DM-RS 如何辅助解调？ |
| 四步竞争随机接入 | Msg1 PRACH → Msg2 PDCCH / PDSCH → Msg3 PUSCH → Msg4 PDSCH | PRACH 前导相关能输出什么？RAR 和竞争解决在哪一步出现？ |
| 测量与解调 | SRS 探测上行，CSI-RS 测量下行，DM-RS 估计解调所需信道，PT-RS 跟踪公共相位 | UE 的下行 CSI 反馈与项目基于 SRS 选出的上行 RI/TPMI 各用于哪个方向？ |

表中是协议层面的关联。仓库用显式资源演示各段收发。完整接入与调度、CSI 报告和共享信道自动插入 PT-RS 的支持范围见[功能矩阵](feature_matrix.md)。控制、随机接入和数据过程分别见 [TS 38.213 V15.3.0](https://www.etsi.org/deliver/etsi_ts/138200_138299/138213/15.03.00_60/ts_138213v150300p.pdf) 与 [TS 38.214 V15.3.0](https://www.etsi.org/deliver/etsi_ts/138200_138299/138214/15.03.00_60/ts_138214v150300p.pdf)。

## 第二遍按问题查协议

| 我想查什么 | 固定 R15 原文章节 |
|---|---|
| 帧结构、RE / RB / BWP、CP、波形 | TS 38.211 V15.2.0 §4.2～4.4、§5.3～5.4 |
| 公共调制和序列 | TS 38.211 V15.2.0 §5.1～5.2。接着读 [NRCommon](../src/common/NRCommon.md) |
| PBCH、PDCCH、PDSCH 的物理映射 | TS 38.211 V15.2.0 §7.3；同步信号与 SSB 位置查 §7.4.2～7.4.3 |
| PUSCH、PUCCH、PRACH 的物理映射 | TS 38.211 V15.2.0 §6.3；比较 PUCCH 格式时先看原表 6.3.2.1-1 |
| DM-RS、PT-RS、SRS、CSI-RS | TS 38.211 V15.2.0 §6.4.1、§7.4.1。先找对应信道，再看端口、序列和映射 |
| CRC、Polar、LDPC、速率匹配 | TS 38.212 V15.2.0 §5 查公共编码，§6 查上行 UL-SCH / UCI，§7 查下行 BCH / DL-SCH / DCI |
| 接入、反馈、搜索空间 | TS 38.213 V15.3.0 §8 查随机接入、§9 查 UCI、§10 和 §13 查 PDCCH 监测 |
| MCS / TBS、CSI、共享信道收发过程 | TS 38.214 V15.3.0 §5 查下行和 CSI，§6 查上行 |

本地 PDF、版本和项目实现的原表追溯见[协议清单](spec_manifest.md)。可直接打开 [TS 38.211 V15.2.0](https://www.etsi.org/deliver/etsi_ts/138200_138299/138211/15.02.00_60/ts_138211v150200p.pdf) 和 [TS 38.212 V15.2.0](https://www.etsi.org/deliver/etsi_ts/138200_138299/138212/15.02.00_60/ts_138212v150200p.pdf)。

## 运行方式与最后一练

在仓库根目录执行，已有虚拟环境可直接运行第三行。VS Code 的 Python 解释器选择仓库里的 `.venv\Scripts\python.exe`。示例图会在运行时显示。

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev,plots]"
.venv\Scripts\python.exe -X utf8 examples/common/NROFDM_demo.py
.venv\Scripts\python.exe -X utf8 examples/pucch/NRPUCCH0_multiuser_demo.py
```

最后用同一个 100 MHz / 30 kHz 载波，选跑 PDSCH、PRACH 和一个参考信号示例。给每个例子记下四项：**承载内容、时间位置、频率位置、接收判决或测量结果**。在 PDSCH 例子里再记下数据与 DM-RS 各占多少 RE。想深入接收机时，再比较单层与四层的信道矩阵和均衡星座。[100 MHz 用例矩阵](validation/NR100MHz_30kHz_validation.md) · [PDSCH 四层示例](../examples/pdsch/NRPDSCH_mimo_demo.py) · [PUSCH 四层示例](../examples/pusch/NRPUSCH_mimo_demo.py)
