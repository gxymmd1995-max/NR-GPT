# 功能覆盖

以下是项目进度表，不是协议原表。具体规范依据在各类文档与规范清单中。

| 模块 | 当前状态 | 单元测试与文档 | MATLAB 比对 |
|---|---|---|---|
| NRCell | 已实现 TDD/FDD 元数据、收发天线数、单 numerology、载波/BWP、Tc/Ts、FFT/采样率、逐符号 CP 及精确采样时序 | `tests/unit/test_NRCell.py`、[`src/cell/NRCell.md`](../src/cell/NRCell.md) | R2024a 5G Toolbox 78 组配置，载波/FFT/采样率/完整子帧时序对比 |
| ExampleLogger | 已实现三个 Python 示例的调用链、参数/出口值/耗时、完整变量快照及异常日志 | `tests/unit/test_ExampleLogger.py`、[`src/diagnostics/ExampleLogger.md`](../src/diagnostics/ExampleLogger.md) | 标准库工程诊断，不对应物理信道，无需 MATLAB 算法向量 |
| NRGrid | 未实现 | 待实现时同时提供 | 待提供 |
| NRCommon | 未实现 | 待实现时同时提供 | 按算法提供独立参考 |
| SSB | 未实现 | 待实现时同时提供 | 必须提供 |
| PDSCH | 未实现 | 待实现时同时提供 | 必须提供 |
| PDCCH | 未实现 | 待实现时同时提供 | 必须提供 |
| PUSCH | 未实现 | 待实现时同时提供 | 必须提供 |
| PUCCH | 未实现 | 待实现时同时提供 | 必须提供 |
| PRACH | 未实现 | 待实现时同时提供 | 必须提供 |
| SRS | 未实现 | 待实现时同时提供 | 必须提供 |

NRCell 通过不代表全部 R15 射频配置或物理层一致性认证通过。具体信道的逐比特、序列、索引、网格、波形等对比须在对应模块实现时完成。
