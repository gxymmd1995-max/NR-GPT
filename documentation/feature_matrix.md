# 功能覆盖

以下是项目进度表，不是协议原表。具体规范依据在各类文档与规范清单中。

| 模块 | 当前状态 | 单元测试与文档 | MATLAB 比对 |
|---|---|---|---|
| NRCell | 已实现 TDD/FDD 元数据、收发天线数、单 numerology、载波/BWP、Tc/Ts、FFT/采样率、逐符号 CP 及精确采样时序 | `tests/unit/test_NRCell.py`、[`src/cell/NRCell.md`](../src/cell/NRCell.md) | R2024a 5G Toolbox 78 组配置，载波/FFT/采样率/完整子帧时序对比 |
| ExampleLogger | 已接入 NRCell 与 NRGrid 的 Python 示例，记录调用链、参数/出口值/耗时、完整变量快照及异常 | `tests/unit/test_ExampleLogger.py`、[`src/diagnostics/ExampleLogger.md`](../src/diagnostics/ExampleLogger.md) | 标准库工程诊断，不对应物理信道，无需 MATLAB 算法向量 |
| NRGrid | 已实现单时隙端口域网格、BWP 坐标、映射/提取/预留/清理、原子冲突保护及 MATLAB 轴转换 | `tests/unit/test_NRGrid.py`、[`src/grid/NRGrid.md`](../src/grid/NRGrid.md) | R2024a 5G Toolbox 18 组配置，网格/索引/复数值/位置加权和对比 |
| 信道配色 | 已实现 18 类固定颜色、别名与 UE 后缀归并、未知标签灰色、动态图例 | `tests/unit/test_channel_colors.py`、[配色接口](../src/grid/channel_colors.md) | 软件显示约定，不改变数值网格，无需伪造 MATLAB 信道向量 |
| NRCommon | 未实现 | 待实现时同时提供 | 按算法提供独立参考 |
| SSB | 未实现 | 待实现时同时提供 | 必须提供 |
| PDSCH | 未实现 | 待实现时同时提供 | 必须提供 |
| PDCCH | 未实现 | 待实现时同时提供 | 必须提供 |
| PUSCH | 未实现 | 待实现时同时提供 | 必须提供 |
| PUCCH | 未实现 | 待实现时同时提供 | 必须提供 |
| PRACH | 未实现 | 待实现时同时提供 | 必须提供 |
| SRS | 未实现 | 待实现时同时提供 | 必须提供 |

NRCell 通过不代表全部 R15 射频配置或物理层一致性认证通过。具体信道的逐比特、序列、索引、网格、波形等对比须在对应模块实现时完成。
