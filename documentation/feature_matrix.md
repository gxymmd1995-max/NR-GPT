# 功能覆盖

以下是项目进度表，不是协议原表。具体规范依据在各类文档与规范清单中。

| 模块 | 当前状态 | 单元测试与文档 | MATLAB 比对 |
|---|---|---|---|
| NRCell | 已实现 TDD/FDD 元数据、收发天线数、单 numerology、载波/BWP、Tc/Ts、FFT/采样率、逐符号 CP 及精确采样时序 | `tests/unit/test_NRCell.py`、[`src/cell/NRCell.md`](../src/cell/NRCell.md) | R2024a 5G Toolbox 78 组配置，载波/FFT/采样率/完整子帧时序对比 |
| ExampleLogger | 已接入 NRCell、NRGrid、NRSRS 的 Python 示例，记录调用链、参数/出口值/耗时、完整变量快照及异常 | `tests/unit/test_ExampleLogger.py`、[`src/diagnostics/ExampleLogger.md`](../src/diagnostics/ExampleLogger.md) | 标准库工程诊断，不对应物理信道，无需 MATLAB 算法向量 |
| NRGrid | 已实现单时隙端口域网格、BWP 坐标、映射/提取/预留/清理、原子冲突保护及 MATLAB 轴转换 | `tests/unit/test_NRGrid.py`、[`src/grid/NRGrid.md`](../src/grid/NRGrid.md) | R2024a 5G Toolbox 18 组配置，网格/索引/复数值/位置加权和对比 |
| 信道配色 | 已实现 18 类固定颜色、别名与 UE 后缀归并、未知标签灰色、动态图例 | `tests/unit/test_channel_colors.py`、[配色接口](../src/grid/channel_colors.md) | 软件显示约定，不改变数值网格，无需伪造 MATLAB 信道向量 |
| NRCommon | 已实现公共Gold PRBS/offset片段与SRS u/v获取，NRSRS已调用；OFDM见独立NROFDM类，其他调制/编码待实现 | 22项单元测试、[NRCommon.md](../src/common/NRCommon.md)、[示例](../examples/common/README.md) | 20组真实MATLAB nrPRBS比特逐位对比，SRS u/v复用832组实测中的活跃配置 |
| NROFDM / NRPhaseRotation | common内单slot CP-OFDM、精确CP、逐符号相位补偿、提前FFT窗口及定时分析因子；无加窗/重采样/PRACH | [OFDM类](../src/common/NROFDM.md)、[相位类](../src/common/NRPhaseRotation.md)、对应单元测试 | 28组真实MATLAB OFDM/相位、84组含扰动接收输入解调 |
| NRChannel | channel内整数TA、RAR/相对TA命令换算、复AWGN、连续CFO及已知逆旋转 | [类文档](../src/channel/NRChannel.md)、[时域SRS示例](../examples/channel/README.md) | 24组独立MATLAB模型；时域SRS集成测得3样点残余时延、RI2/TPMI0 |
| NRUplinkCodebook | R15 1/2/4端口全部标准矩阵；互信息搜索上行RI/TPMI，支持外部rank/候选限制 | [类文档](../src/common/NRUplinkCodebook.md)、`tests/unit/test_NRUplinkCodebook.py` | 72个实际nrPUSCHCodebook矩阵；接收场景独立验证选择 |
| NRSRSReceiver | 频域多用户联合FIR信道估计、静默RE/残差噪声、逐PRB噪声、首径/最强径/平均/RMS时延及上行RI/TPMI | [类文档](../src/srs/NRSRSReceiver.md)、`tests/unit/test_NRSRSReceiver.py`、[示例](../examples/srs/README.md) | 24组真实MATLAB输入、32用户结果，完整CIR/H/噪声/决策；[验证](validation/NRSRSReceiver_validation.md) |
| SSB | 未实现 | 待实现时同时提供 | 必须提供 |
| PDSCH | 未实现 | 待实现时同时提供 | 必须提供 |
| PDCCH | 未实现 | 待实现时同时提供 | 必须提供 |
| PUSCH | 未实现 | 待实现时同时提供 | 必须提供 |
| PUCCH | 未实现 | 待实现时同时提供 | 必须提供 |
| PRACH | 未实现 | 待实现时同时提供 | 必须提供 |
| NRSRS | 已实现R15端口/梳齿/带宽/跳变/重复/候选时隙/NRGrid映射；接收由NRSRSReceiver、时域波形由NROFDM、信道作用由NRChannel负责，调度/功控待实现 | 109项发送单元测试、[NRSRS.md](../src/srs/NRSRS.md)、[示例](../examples/srs/README.md) | 832组发送参考及接收/时域链路独立对照；[记录](validation/NRSRS_validation.md) |

NRCell 通过不代表全部 R15 射频配置或物理层一致性认证通过。具体信道的逐比特、序列、索引、网格、波形等对比须在对应模块实现时完成。
