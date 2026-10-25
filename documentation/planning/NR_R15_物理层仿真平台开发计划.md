# NR Release 15 Python 物理层仿真平台开发计划

项目目录：`D:\doc\code\python\NR1024`  
计划日期：2026-10-24  
状态：NRCell、ExampleLogger 和 NRGrid 单时隙端口域网格已实现并验证；公共波形及具体物理信道尚未实现。见[NRCell 类文档](../../src/cell/NRCell.md)、[NRGrid 类文档](../../src/grid/NRGrid.md)和[覆盖矩阵](../feature_matrix.md)。

2026-10-24 补充约束：协议原文与译文统一放在 `documentation/protocols/`；项目设计和验证报告放在 `documentation/` 的其他子目录。类源码直接放在 `src/<模块>/`，类说明与源码同级；示例按照源码模块组织到 `examples/<模块>/`，生成的中间文件、MATLAB 参考数据和图片均与示例脚本同级。每个类必须有单元测试和详细 Markdown 说明，逐项解释字段、属性、函数及示例，并在适用时配图。规范表格、公式须标明原文版本与章节，具体物理信道必须与 MATLAB 独立比对。GitHub 目标为 `gxymmd1995-max/NR-GPT`；等待用户明确通知后才能提交或推送。

## 1. 目标与实施原则

建立基于 3GPP NR Release 15 的 Python 链路级物理层仿真平台，覆盖 NRCell、NRGrid、NRCommon、SSB、PDSCH、PDCCH、PUSCH、PUCCH、PRACH、SRS，并逐步补齐编码、参考信号、OFDM、接收机、信道模型和性能统计。

平台需要支持三类用途：

1. 学习与算法验证：查看比特、序列、调制符号、资源映射、时域波形等中间结果。
2. 链路性能研究：进行 BER、BLER、EVM、同步误差、PRACH 检测概率等仿真。
3. 后续扩展：支持多天线、不同 BWP、混合 numerology 和更多 R15 配置。

遵循“先正确、后完整、再优化”的顺序。标准规定的发射侧处理与平台自行选择的接收算法分开记录；接收机使用 LS、LMMSE、MMSE、SCL 等算法，并不意味着这些算法本身由 3GPP 强制规定。

## 2. 标准基线与现有资料

Release 15 不是单一版本号。每份规范必须固定具体版本，形成 `documentation/spec_manifest.md`，记录版本、文件、来源、校验值、涉及章节和已知差异。

| 规范 | 用途 | 当前目录情况与处理计划 |
|---|---|---|
| TS 38.211 | 物理信道、调制、序列、资源映射及波形 | 当前目录使用官方 V15.2.0 英文 PDF 和辅助中文译文；无 R18 PDF |
| TS 38.212 | 复用、CRC、Polar、LDPC、速率匹配 | 有 V15.2.0 英文 PDF；中文 Markdown 仅作辅助，须核查完整性 |
| TS 38.213 | 控制相关物理层过程 | 有 V15.3.0 英文 PDF |
| TS 38.214 | 数据相关物理层过程 | 有 V15.3.0 英文 PDF |
| TS 38.215 | 物理层测量 | 后续补充并固定 R15 版本 |
| TS 38.104 | 基站射频、带宽及相关参数约束 | 有 V15.2.0 英文 PDF |
| TS 38.331 | RRC 参数定义与配置约束 | 有 V15.2.1 英文 PDF；只提取物理层需要的配置，不实现完整 RRC |
| TR 38.901 | TDL/CDL 信道模型 | 实现衰落信道阶段补充并固定适用版本 |

首轮暂按现有 R15 文档版本建立候选基线；启动实现前检查跨规范引用和勘误。若某项功能在该具体版本中尚不完整，应明确调整基线或延期，不能直接搬入 R16/R17/R18 行为。

官方资料入口：

- [3GPP 规范目录](https://portal.3gpp.org/Specifications.aspx)
- [ETSI TS 38.211 V15.2.0](https://www.etsi.org/deliver/etsi_ts/138200_138299/138211/15.02.00_60/ts_138211v150200p.pdf)
- [ETSI TS 38.212 V15.2.0](https://www.etsi.org/deliver/etsi_ts/138200_138299/138212/15.02.00_60/ts_138212v150200p.pdf)

## 3. 范围与默认场景

### 3.1 首个可运行版本

- 单小区、单用户、FR1、单 BWP、单 numerology。
- 常规 CP，先支持 15/30 kHz SCS；默认示例采用 30 kHz、52 RB，具体射频参数在规范核对后确定。
- SISO、单层、单码字；先支持 QPSK，再扩展 16/64/256QAM 中适用的配置。
- 理想信道与 AWGN；先采用已知定时和理想信道估计，再切换到实际同步与估计。
- 支持网格级与时域波形级两种仿真入口。
- 调度由静态配置或脚本提供，不实现完整 MAC/RLC/PDCP/RRC 协议栈。

第一个里程碑是 SSB 生成、OFDM、无噪声接收及 PBCH CRC 通过；第一个数据链路里程碑是含 LDPC 和 DM-RS 的 PDSCH 传输块闭环。

### 3.2 完整平台的后续覆盖

- R15 范围内的其他 SCS、扩展 CP 适用场景、FR2 及 SSB Case。
- PUCCH Format 0–4、PRACH 长短前导及各格式、SRS 多种资源配置。
- PUSCH transform precoding、UCI 复用；PDSCH/PUSCH 多层与预编码。
- DM-RS 多端口及不同映射配置、PT-RS、CSI-RS、CSI-IM 和 CSI 测量。
- TDL/CDL、多普勒、频偏、定时偏差、多天线和 HARQ 软合并。
- 多 BWP 和混合 numerology 通过独立网格、频移及采样率协调集成，避免在单一网格内混用坐标。

维护功能覆盖表，分别标注“未实现、发射可用、理想接收可用、实际接收可用、独立向量验证通过”。部分配置可用不能表述为完整 R15 一致性通过。

## 4. 模块职责

| 模块 | 职责 | 关键输出或边界 |
|---|---|---|
| NRCell | 小区、载波、BWP、帧时序、TDD/FDD 和配置校验 | 统一配置对象及派生参数；不堆放信号处理算法 |
| NRGrid | 频域网格、坐标转换、资源分配、冲突检查、可视化 | 复数网格与独立占用信息，支持端口域与天线域 |
| NRCommon | Gold/低 PAPR 序列、调制解调、比特运算及公共数学工具 | 无业务状态、可复用的底层函数 |
| SSB | PSS、SSS、PBCH、PBCH DM-RS、SSB 映射与检测 | PCI 检测、定时、PBCH 解码及 MIB 比特字段 |
| PDCCH | DCI 编解码、Polar、CORESET、REG/CCE 映射、DM-RS 和候选搜索 | 先固定候选，再实现 Search Space 与盲检 |
| PDSCH | DL-SCH、LDPC、速率匹配、层映射、DM-RS/PT-RS、资源映射与接收 | 传输块与 CRC、软比特、译码统计 |
| PUSCH | UL-SCH、LDPC、DM-RS/PT-RS、CP-OFDM/DFT-s-OFDM、UCI 复用 | 上行数据闭环；变换预编码相关处理独立校验 |
| PUCCH | Format 0–4、UCI 编码、跳频、序列与 DM-RS、检测和解码 | 各 Format 分别验收，不能全部套用 Polar |
| PRACH | 前导序列、循环移位、格式、时域波形和相关检测 | 前导索引、到达时延、检测/虚警统计 |
| SRS | 序列、comb、循环移位、端口、跳频及资源映射 | 上行信道探测与估计结果 |
| coding | CRC、Polar、LDPC、短块编码、速率匹配/恢复 | 供 PBCH/DCI/DL-SCH/UL-SCH/UCI 复用 |
| waveform | OFDM 调制解调、CP、采样率与波形元数据 | 处理逐符号 CP 长度、FFT 归一化和载频相位约定 |
| channel_models | 理想信道、AWGN、衰落、射频损伤 | 独立随机数生成器、噪声功率及信道真值 |
| receiver | 同步、信道估计、插值、均衡、噪声估计 | 支持理想与实际算法切换 |
| simulation | 场景执行、SNR 扫描、结果汇总、复现实验 | 配置、种子、代码版本、统计区间及结果文件 |

PBCH 归属 SSB；DM-RS 等参考信号跟随所属信道管理，公共序列算法在 NRCommon 中共享。PRACH 使用独立波形路径，通过时间轴和采样率与上行波形合成。

## 5. 架构与接口约定

基本链路：

```text
场景配置 → NRCell / BWP → 传输块或控制信息
  → 编码与速率匹配 → 加扰与调制 → 层映射 / 预编码
  → 信道及参考信号映射 → NRGrid → OFDM → 信道
  → 同步 / OFDM 解调 → 信道估计与均衡
  → 解调与解扰 → 速率恢复与译码 → CRC / 性能统计
```

约定在第一阶段固定：

1. Python 模块直接放在 `src/` 下，使用 `cell`、`grid` 等小写模块名；类源码和类文档与类名一致，如 `NRCell.py`、`NRCell.md`。相关示例、测试及产物保留类名大小写，如 `NRCell_demo.py`、`test_NRCell.py`、`NRCell_reference.json`。
2. 配置采用 dataclass 和类型标注，区分用户输入、派生参数与运行状态；发现不支持的配置直接报错。
3. 网格统一为 `[port_or_antenna, symbol, subcarrier]`，元数据明确域类型；多时隙按时隙调度和流式处理。
4. 分开定义 Point A、载波 CRB、BWP PRB、SSB 子载波和 FFT bin 坐标；转换函数集中维护。
5. 数组索引从 0 开始，明确规范索引到 Python 索引的转换；比特顺序及 LLR 正负约定必须固定。
6. 接口分为 `encode/decode`、`generate`、`indices`、`map/extract` 和 `modulate/demodulate` 等小函数，不用一个巨型类承担整个链路。
7. 端口到天线必须经过明确的预编码/映射步骤；资源冲突检测允许登记规范规定的复用、打孔和保留资源规则。
8. 区分采样 SNR、Es/N0 和 Eb/N0；记录 FFT、CP、占用带宽及噪声方差换算，避免 BLER 横轴定义不一致。
9. 核心默认使用 float64/complex128 保证参考实现精度，之后评估 float32/complex64 与 Numba 加速。
10. 所有实验显式传入随机种子，保留中间数据导出能力。

目标目录（cell、grid、diagnostics 及其测试/示例已实现，其他模块不提前创建空骨架）：

```text
NR1024/
├── pyproject.toml
├── README.md
├── documentation/
│   ├── protocols/       # 仅协议原文和译文
│   ├── planning/        # 开发计划
│   ├── validation/      # 验证报告
│   ├── spec_manifest.md
│   ├── architecture.md
│   └── feature_matrix.md
├── src/
│   ├── cell/           # NRCell.py、NRCell.md
│   ├── grid/
│   ├── common/
│   ├── coding/
│   ├── waveform/
│   ├── channels/       # ssb/pdcch/pdsch/pusch/pucch/prach/srs
│   ├── reference_signals/
│   ├── channel_models/
│   ├── receiver/
│   └── simulation/
├── configs/
├── examples/
│   └── cell/           # 示例脚本、MATLAB 脚本、JSON 中间数据和 PNG/SVG
└── tests/              # 当前 unit/matlab；后续可增加 integration
```

## 6. 分阶段开发与验收

以下为单名熟悉通信算法的开发者的粗略工作量，不构成交付日期承诺；独立向量获取、译码器性能和配置覆盖会影响工期。

| 阶段 | 工作内容 | 可检查交付物与退出条件 | 参考工作量 |
|---|---|---|---|
| P0 规范与接口 | 固定规范、功能矩阵、坐标/功率/比特约定、测试来源 | 每个首期功能关联规范章节，候选基线差异有结论 | 3–5 天 |
| P1 基础平台 | 工程、NRCell、NRGrid、NRCommon、OFDM、AWGN、绘图 | 网格映射无非法冲突；OFDM 回环相对误差目标 < 1e-10，明确零输入处理 | 1–2 周 |
| P2 编码与 SSB | CRC、PBCH 所需 Polar、PSS/SSS/PBCH/DM-RS、同步 | 固定 PCI/SSB 配置独立向量比对；无噪声恢复 PCI 与 PBCH，CRC 通过 | 2–3 周 |
| P3 PDSCH | LDPC、速率匹配/恢复、TBS、DM-RS、数据映射、均衡 | 单层 QPSK 无噪声传输块逐比特恢复；AWGN 输出可复现 BLER 曲线 | 3–5 周 |
| P4 PDCCH 与下行集成 | DCI、CORESET、Search Space、控制 Polar、候选搜索 | DCI 控制后续 PDSCH 资源及 MCS；有效候选通过 CRC，记录盲检误检 | 2–3 周 |
| P5 PUSCH | 先 CP-OFDM 数据闭环，再 DFT-s-OFDM 与 UCI 复用 | 无噪声 UL-SCH 恢复，DM-RS 与两种波形路径分别比对 | 2–4 周 |
| P6 PUCCH | Format 0/1，再 2/3/4；UCI 处理与接收 | 各 Format 分别有独立样例和支持范围，测量 UCI 错误率 | 3–5 周 |
| P7 PRACH 与 SRS | 先一种长/短前导和单端口 SRS，再扩展格式 | 已知前导与延迟检测正确；噪声下给出检测/虚警率；SRS 估计与真值比较 | 2–4 周 |
| P8 性能与覆盖扩展 | TDL/CDL、MIMO、HARQ、PT-RS/CSI-RS、FR2 等 | 逐项更新覆盖矩阵，回归原有链路，产出基准报告 | 按配置集拆分估算 |

P0–P7 顺序投入约 16–28 周，仅覆盖逐步扩展的链路平台，不代表所有 R15 配置完整实现。P2 之后即可交付第一个可运行演示，P3 之后具备基础数据链路仿真能力。

LDPC 和 Polar 是关键依赖，应尽早获取独立测试向量并验证译码器。PDCCH 可以在 PDSCH 稳定前进行独立开发；实际集成时再由 DCI 驱动数据链路。

## 7. 验证策略

### 7.1 分层验证

- 公共算法：CRC、Gold、QAM、LLR、序列、FFT、CP、PRB/RE 索引、TBS 边界。
- 编码：编码结果、码块分段、填充位、各 RV、速率匹配长度与恢复过程；不能仅做自编码自解码。
- 信道：分别验证调制符号、参考信号、RE 索引、映射后的网格及波形。
- 链路：先已知定时与理想信道，再启用估计误差和同步误差，隔离问题来源。
- 性能：记录帧数、错误块数、置信区间和停止规则；不将零错误直接报告为真实 BLER 等于零，也不要求有限样本结果严格单调。

### 7.2 独立参考

具体物理信道/信号必须使用 MATLAB 5G Toolbox 独立生成参考结果并逐项比对，保存生成脚本、输入、环境版本、原始结果和误差容限。成熟开源实现或独立公式实现可作为补充。外部实现必须核对 Release、配置、比特序和归一化约定，不能作为无条件标准真值。

每个向量保存来源、许可条件、生成版本、参数、随机种子、预期结果和误差容限。没有独立参考时，明确标记验证缺口。

### 7.3 各阶段演示

- P1：资源栅格、OFDM 时域/频谱、星座图。
- P2：SSB 网格、PSS 相关峰、PCI 与 PBCH 解码结果。
- P3/P4：PDSCH BER/BLER、DCI 调度资源可视化。
- P5/P6：上行波形、PUSCH BLER、各 PUCCH Format 的 UCI 错误率。
- P7：PRACH 时延相关峰、检测与虚警曲线、SRS 信道估计误差。

## 8. 技术栈与运行方式

- Python 3.11 或更新的兼容版本；实际启动时固定解释器和依赖版本。
- NumPy、SciPy：数组、FFT、滤波和基础数值运算。
- Matplotlib：网格、星座、频谱及性能曲线。
- pytest：单元、参考向量和集成回归。
- Numba：完成正确性与性能剖析后作为可选加速依赖。
- Jupyter：可选教学与调试入口；核心逻辑保留在 Python 包中。
- JSON 配置起步，必要时增加 YAML；使用脚本/CLI 执行示例与 SNR 扫描。

每次仿真导出配置、种子、规范基线标识、环境版本、统计结果 CSV/JSON 和图表。首期使用命令行与示例脚本，图形界面作为后续需求。

## 9. 主要风险与控制措施

| 风险 | 对应措施 |
|---|---|
| R15 与 R18 混用、翻译遗漏 | 固定英文规范基线，中文只作辅助，每个算法关联章节 |
| 编码器与译码器共享错误导致自测通过 | 使用独立参考向量检查中间步骤 |
| 坐标、CP、端口和幅度约定不一致 | P0 冻结约定，并用边界场景测试 |
| Python 译码耗时过长 | 先单链路正确性，再剖析和加速；设置统计停止规则 |
| 配置组合数量过多 | 维护支持矩阵，不支持的组合显式拒绝 |
| 将算法演示误当作完整协议实现 | 明确静态调度、RRC 配置输入及链路仿真边界 |

## 10. 下一步实施清单

1. 已补齐官方 TS 38.211 V15.2.0，后续信道实现前继续核对整套 R15 候选基线。
2. 已编写规范清单、覆盖矩阵及架构说明。
3. 已创建 Python 包、依赖配置和基础测试结构。
4. 已实现 `NRCell`、`NRGrid` 及基础坐标、映射和资源冲突管理。
5. 实现 Gold、基础调制解调、OFDM 与 AWGN，并通过基础回环。
6. 进入 SSB 与 PBCH，实现第一个端到端样例。

当前 NRCell 已完成单元测试、MATLAB 载波/OFDM 时序比对及类文档。支持 TDD/FDD 元数据、收发天线数量、Tc/Ts、基于频域 RE 数的 2 次幂 FFT 选择及精确 CP 采样时序。NRGrid 已完成单时隙端口域数据/占用分离、BWP 坐标、映射/预留/提取和 MATLAB 轴对比；天线域预编码与实际波形模块仍待实施。最新完成情况见[覆盖矩阵](../feature_matrix.md)。
