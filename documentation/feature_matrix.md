# 功能覆盖

以下是项目进度表，不是协议原表。具体规范依据在各类文档与规范清单中。

| 模块 | 当前状态 | 单元测试与文档 | MATLAB 比对 |
|---|---|---|---|
| NRCell | 已实现 TDD/FDD 元数据、收发天线数、单 numerology、载波/BWP、Tc/Ts、FFT/采样率、逐符号 CP 及精确采样时序 | `tests/unit/test_NRCell.py`、[`src/cell/NRCell.md`](../src/cell/NRCell.md) | R2024a 5G Toolbox 78 组配置，载波/FFT/采样率/完整子帧时序对比 |
| ExampleLogger | 已接入 NRCell、NRGrid、NRSRS 的 Python 示例，记录调用链、参数/出口值/耗时、完整变量快照及异常 | `tests/unit/test_ExampleLogger.py`、[`src/diagnostics/ExampleLogger.md`](../src/diagnostics/ExampleLogger.md) | 标准库工程诊断，不对应物理信道，无需 MATLAB 算法向量 |
| NRGrid | 已实现单时隙端口域网格、BWP 坐标、映射/提取/预留/清理、原子冲突保护及 MATLAB 轴转换 | `tests/unit/test_NRGrid.py`、[`src/grid/NRGrid.md`](../src/grid/NRGrid.md) | R2024a 5G Toolbox 18 组配置，网格/索引/复数值/位置加权和对比 |
| 信道配色 | 已实现 18 类固定颜色、别名与 UE 后缀归并、未知标签灰色、动态图例 | `tests/unit/test_channel_colors.py`、[配色接口](../src/grid/channel_colors.md) | 软件显示约定，不改变数值网格，无需伪造 MATLAB 信道向量 |
| NRCommon | 已实现Gold PRBS/offset、SRS u/v、12点低PAPR、PUCCH逐符号参数；OFDM见独立类 | 36项单元测试、[NRCommon.md](../src/common/NRCommon.md)、[示例](../examples/common/README.md) | 20组真实MATLAB nrPRBS比特逐位对比，SRS u/v复用832组实测中的活跃配置 |
| NROFDM / NRPhaseRotation | common内单slot CP-OFDM、精确CP、逐符号相位补偿、提前FFT窗口及定时分析因子；无加窗/重采样/PRACH | [OFDM类](../src/common/NROFDM.md)、[相位类](../src/common/NRPhaseRotation.md)、对应单元测试 | 28组真实MATLAB OFDM/相位、84组含扰动接收输入解调 |
| NRChannel | channel内整数TA、RAR/相对TA命令换算、复AWGN、连续CFO及已知逆旋转 | [类文档](../src/channel/NRChannel.md)、[时域SRS示例](../examples/channel/README.md) | 24组独立MATLAB模型；时域SRS集成测得3样点残余时延、RI2/TPMI0 |
| NRUplinkCodebook | R15 1/2/4端口全部标准矩阵；互信息搜索上行RI/TPMI，支持外部rank/候选限制 | [类文档](../src/common/NRUplinkCodebook.md)、`tests/unit/test_NRUplinkCodebook.py` | 72个实际nrPUSCHCodebook矩阵；接收场景独立验证选择 |
| NRSRSReceiver | 频域多用户联合FIR信道估计、静默RE/残差噪声、逐PRB噪声、首径/最强径/平均/RMS时延及上行RI/TPMI | [类文档](../src/srs/NRSRSReceiver.md)、`tests/unit/test_NRSRSReceiver.py`、[示例](../examples/srs/README.md) | 24组真实MATLAB输入、32用户结果，完整CIR/H/噪声/决策；[验证](validation/NRSRSReceiver_validation.md) |
| SSB | 未实现 | 待实现时同时提供 | 必须提供 |
| PDSCH | 未实现 | 待实现时同时提供 | 必须提供 |
| PDCCH | 未实现 | 待实现时同时提供 | 必须提供 |
| PUSCH | 未实现 | 待实现时同时提供 | 必须提供 |
| PUCCH | Format0/1/2/3/4资源及完整时域收发已实现；F2/F3/F4公共小块/Polar UCI | [三类文档及示例](../examples/pucch/README.md)，每类单测+时域集成 | 960组序列/坐标、40组时域/候选/Toolbox UCI，扩展CP按固定R15显式适配 |
| PRACH | 未实现 | 待实现时同时提供 | 必须提供 |
| NRSRS | 已实现R15端口/梳齿/带宽/跳变/重复/候选时隙/NRGrid映射；接收由NRSRSReceiver、时域波形由NROFDM、信道作用由NRChannel负责，调度/功控待实现 | 109项发送单元测试、[NRSRS.md](../src/srs/NRSRS.md)、[示例](../examples/srs/README.md) | 832组发送参考及接收/时域链路独立对照；[记录](validation/NRSRS_validation.md) |

NRCell 通过不代表全部 R15 射频配置或物理层一致性认证通过。具体信道的逐比特、序列、索引、网格、波形等对比须在对应模块实现时完成。


阶段显示：NRPlotConfig/NRStagePlotter提供字段开关与通配符选择；PUCCH F0链路27阶段可直接交互显示，默认不保存图片，NROFDM内部波形/频谱也使用实际中间数据。关闭时不导入Matplotlib；CI绘图测试安装dev,plots并用Agg测试后端验证显示调用，GUI脚本不强制Agg。

PUCCH F0多用户CDM：已支持通过完整候选集合互斥的循环移位配置，在共享时频资源上逐用户检测；三UE时域叠加与DTX已有实际MATLAB12例/36UE比对。要求共享已知同步、每RB内近似平坦信道，未实现联合均衡/SIC。见[验证报告](validation/NRPUCCH0_multiuser_validation.md)。

PUCCH F1：已实现1/2bit UCI、4～14符号（受CP限制）、数据/DMRS、OCC、组跳变、slot内跳频、完整时域收发与DMRS辅助MRC。未实现SR资源选择、跨slot重复、盲同步、多用户联合均衡。实际MATLAB普通CP/QPSK68组通过；扩展CP和BPSK目前只有Python链路测试，尚未独立MATLAB验证。

PUCCH F2：首版3～11位UCI小块编码/软ML，1/2符号、连续1～16RB、加扰QPSK、DMRS、slot内跳频及完整时域收发。实际MATLAB普通CP36组通过；扩展CP和噪声/CFO链路目前仅Python测试。12位以上Polar、CRC、字段语义组装和完整调度尚未实现；码率上限0.6，强频选/多用户联合均衡未实现。

新增Common编码核：Polar指定N/零PC位母码及SC；NR LDPC BG1/BG2单码块及分层归一化最小和；经典RM(r,m)及多数逻辑译码。Polar CRC/SCL/PC位/速率匹配、LDPC分段/CRC/速率匹配仍待实现，尚未解除PUCCH F2的12位以上限制。详见各类.md。

当前更新（取代前文F2首版限制）：PUCCH2/3通过NRUCICode支持3～1706位UCI，小块/Polar、CRC6/11、PC位、完整速率匹配和双块分段；资源不足按含CRC码率0.6拒绝。F3支持4～14符号（受CP限制）、合法DFT带宽、QPSK/π/2-BPSK、DMRS/额外DMRS及跳频。接收为PC约束SC，不包含CRC辅助SCL、盲同步或强频选均衡。实际MATLAB：UCI15例、F2 56例、F3 22例，详见validation/NRPUCCH3_validation.md。

PUCCH F4：已实现固定1RB、SF2/4及全部OCC、QPSK/π/2-BPSK、DMRS/额外DMRS/跳频、公共小块/Polar UCI及完整时域收发。实际MATLAB普通CP单用户132组通过；普通/扩展CP带噪链路、四用户OCC复用有Python测试，尚无独立MATLAB该类多用户/扩展CP向量。接收平坦每跳信道，非联合均衡或SCL。

PUSCH已扩展1～4层单码字CP-OFDM、连续RB、QPSK/16/64/256QAM、Type-A位置2/3、DMRS Type1/2单/双符号、附加位置与频域/时域OCC端口；每RB联合LS估计有效MIMO信道并ZF均衡、逆层映射及UL-SCH解码。实际MATLAB新增64例MIMO及原32例单层通过；公共UL-SCH5例保留。见[验证报告](validation/NRPUSCH_mimo_validation.md)。扩展CP/噪声/CFO/延迟仅Python链路验证；不含多码块、HARQ合并、DFT-s-OFDM、动态TPMI预编码、UCI/PTRS、Type-B、跳频或时变信道插值。

PDSCH当前：1～4层单码字、Type-A DMRS Type1/2、单/双符号、附加位置及端口OCC；单码块DL-SCH/Nref、联合LS信道估计与ZF均衡。实际MATLAB：原单层32例+多层64例、DL-SCH5例；普通/扩展CP带噪MIMO、秩亏拒绝有Python测试。5～8层/双码字、Type-B、多码块、动态预编码、频选/时间插值、MMSE、PTRS/预留RE及HARQ合并仍待扩展。

PRACH：固定R15，长0/1/2/3与短A1/A2/A3/B1/B2/B3/B4/C0/C2，非受限集合、64前导、ZC/DFT、独立FFT/CP、BWP频域映射、短格式半毫秒CP扩展；实际MATLAB44波形+32序列边界例通过。接收为已知RO/可选已知CFO补偿、周期平均/64候选相关、样点峰值时延与多Rx合并；三UE带噪延迟例通过。无受限Type A/B、完整配置表调度、RAR/Msg3、盲CFO、SIC或分数采样。详见[验证边界](validation/NRPRACH_validation.md)。

PDCCH首版：显式候选、六CRB对齐BWP、duration1/2/3、聚合等级1/2/4/8/16、两种REG映射、单端口DMRS/QPSK和完整DCI Polar/CRC时域收发。实际MATLAB15例通过。无CORESET0/完整SearchSpace盲搜调度、DCI字段打包、allContiguousRBs或SCL。见[验证](validation/NRPDCCH_validation.md)。
