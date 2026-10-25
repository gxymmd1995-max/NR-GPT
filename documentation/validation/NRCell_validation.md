# NRCell 验证记录

验证日期：2026-10-24（Asia/Shanghai）。

## 执行环境与结果

本节保留 2026-10-24 的 NRCell/日志基线结果。2026-10-25 新增 NRGrid 与配色后，全量回归为 191 项测试（189 项单元测试、2 项 MATLAB 独立向量入口），三个模块行/分支覆盖率均为 100%；详见 [NRGrid 验证记录](NRGrid_validation.md)。下面的 131 项是原基线数量，不代表当前全项目数量。

- Python 3.14.0，Windows；pytest 9.1.1，pytest-cov 7.1.0。
- MATLAB R2024a：24.1.0.2537033；5G Toolbox 24.1。
- 131 项 pytest 测试全部通过，无跳过。其中 130 项为单元测试（115 项 NRCell、15 项 ExampleLogger），另一个 MATLAB 对比测试在内部循环逐组检查 78 个配置；不能将这 78 组误报为 pytest 收集的 78 项测试。
- `src/cell` 与 `src/diagnostics` 行覆盖率 100%，分支覆盖率 100%；这仅反映当前 NRCell 的测试覆盖，不等于 R15 全协议一致性认证。
- 源码 docstring 示例通过 doctest；演示脚本和绘图脚本成功运行。

## MATLAB 对比依据与实际产物

生成脚本：[`export_NRCell_reference.m`](../../examples/cell/export_NRCell_reference.m)。  
实际输出：[`NRCell_reference.json`](../../examples/cell/NRCell_reference.json)。  
Python 对比：[`test_NRCell_matlab.py`](../../tests/matlab/test_NRCell_matlab.py)。

MATLAB 独立构造 `nrCarrierConfig`，读取其只读属性，调用 `nrResourceGrid` 实际生成空网格，并用显式 Nfft 调用 `nrOFDMInfo` 生成完整子帧的 CP、符号点数和采样率。输出记录 MATLAB/Toolbox 版本、UTC 生成时间、输入参数和预期尺寸。生成过程中不调用 Python，也不使用 Python 输出作为预期结果。

以下为项目测试矩阵，非 3GPP 原表；参数空间依据 TS 38.211 V15.2.0 §4.2 表 4.2-1、§4.3.2 表 4.3.2-1/-2，尺寸依据 §4.4.2/§4.4.4.1。边界值还参考 TS 38.331 V15.2.1 §6.3.2 和 MATLAB `nrCarrierConfig` 接口。

| 配置维度 | 覆盖值 | 对比项目 |
|---|---|---|
| SCS / CP | 15/30/60/120/240 kHz normal，60 kHz extended，共 6 组 | 符号/slot、slot/subframe、slot/frame |
| 常规载波 | 52 RB，起点 CRB 10，PCI 42，SFN 9，slot 1 | 网格子载波数和符号数 |
| FFT 边界补充 | 10/11、21/22、42/43、85/86、170/171 RB；对应相邻 FFT 档位切换 | FFT、采样率与整数 CP 采样点 |
| 最小尺寸 | 1 RB，起点 0，PCI 0，SFN 0，slot 0 | 最小合法资源网格 |
| 最大接口边界 | 275 RB，起点 2199，PCI 1007，SFN 1023，各 numerology 最后一个 slot | 最大尺寸与边界配置 |

六组 SCS/CP 分别采用 13 组载波，共 78 个配置；每组检查 19 个输出字段（含逐符号数组），展开为 34398 个整数结果，容差为 0。输出包括 FFT、采样率、每采样点 Tc 数、完整子帧 CP/符号长度（采样点与 Tc）、符号起点、当前 slot 的 CP/长度、slot 起点和 slot/子帧/帧采样点总数。

FFT 策略为 max(128, next_power_of_two(12*NSizeGrid))，是平台约定。MATLAB 显式传入 Nfft，Windowing=0，无额外重采样；没有把 MATLAB 默认的占用率 FFT 规则当作项目策略。

此对比验证通用载波尺寸、FFT/采样率和精确 OFDM 采样时序，不验证 RF 频段带宽表、实际非空资源网格、波形调制/解调、译码、BWP 配置、TDD 符号方向或 SFN 推进算法。物理天线数和双工模式是平台元数据，由单元测试检查，不能将逻辑天线端口当作物理天线数。MATLAB R2024a 含有更高 Release 的功能，本脚本仅使用 R15 交集。

## 单元测试范围

- 五种 numerology 与两种 CP 的合法组合。
- 非法 SCS、扩展 CP 误配、PCI/载波/BWP/帧时隙越界。
- 所有整数初始化字段的 bool、浮点数及字符串误用。
- BWP 含于载波的约束，非零载波起点与非零 BWP 起点的区别。
- PRB/CRB 转换、Point A 频偏及坐标边界。
- PCI 分解、平均时隙时长、名义网格占用带宽。
- 正向、负向、多帧时隙推进及 SFN 1023→0 回绕。
- 对象不可变、字典往返重建、MATLAB 参数导出。
- TDD/FDD 合法值及类型、正整数收发天线数量、天线数不改变每分支 FFT。
- FFT 档位两侧边界、固定 Tc/Ts 与 KAPPA、采样率及每采样点 Tc 数。
- 六组 SCS/CP 各遍历全部 275 个合法 RB 宽度，检查整数 CP、子帧 Tc 总数和采样点总数守恒。
- 普通 CP 的子帧长 CP 位置、60 kHz 相邻时隙的精确时长差异、扩展 CP 全符号长度、symbol_timing 参数边界。

## 重现

```powershell
matlab -batch "addpath('examples/cell'); export_NRCell_reference;"
.venv\Scripts\python -m pytest --require-matlab --cov=cell --cov=grid --cov=diagnostics --cov-branch --cov-report=term-missing --cov-fail-under=100
.venv\Scripts\python -m doctest src/cell/NRCell.py
.venv\Scripts\python examples/cell/NRCell_demo.py
.venv\Scripts\python examples/cell/plot_NRCell.py
.venv\Scripts\python examples/cell/plot_NRCell_timing.py
```

没有 MATLAB 时可以运行仓库目录中已有的独立向量检查。若参考 JSON 缺失，默认测试明确跳过；加 `--require-matlab` 时强制失败。CI 配置使用此开关，防止缺失参考数据被报告为验证通过。本记录证明本地 Windows 环境的验证结果；远端 CI 需以 GitHub Actions 实际运行记录为准，不能把 CI 配置视为远端执行通过的证据。

## 命名和数据位置

类名、类文件及关联文件均保留 `NRCell` 大小写。源码/类说明为 `src/cell/NRCell.py`、`NRCell.md`；单元测试为 `test_NRCell.py`，MATLAB 对比为 `test_NRCell_matlab.py`。示例数据和图片与对应脚本同级，格式说明见[示例目录说明](../../examples/cell/README.md)。

## 示例日志验证

三个 Python 示例实际运行生成同级 .log 文件，包含调用路径、参数、出口值、耗时和完整状态快照。ExampleLogger 的 15 项单元测试验证输出隔离、原 profiler 恢复、异常传播、文件覆盖、全部字段/属性输出及回调分支。日志仅为工程诊断，不重新生成或替代 MATLAB 参考向量。详见 [ExampleLogger 类说明](../../src/diagnostics/ExampleLogger.md)。
