# NRCell 示例与生成文件

对应源码和类说明位于 [`src/cell/`](../../src/cell/NRCell.md)。在项目根目录先执行 `python -m pip install -e ".[dev,plots]"`；下面的 Windows 命令使用项目虚拟环境。Linux/macOS 将 `.venv\Scripts\python` 替换为 `.venv/bin/python`。

## 入口与输出

下表是项目文件说明表，不是协议原表。所有默认输出都根据脚本自身的位置确定，和脚本放在同一个目录，不随终端工作目录改变。

三个 Python 示例会额外生成同名 `.log`：`NRCell_demo.log`、`plot_NRCell.log` 和 `plot_NRCell_timing.log`。每次运行覆盖旧日志；文件保存 DEBUG 调用链、参数、出口值、耗时与完整类状态，终端默认显示 INFO 状态快照和摘要。运行失败时记录 traceback 并继续向外抛出原异常。

| 入口 | 功能 | 默认输出 |
|---|---|---|
| [`NRCell_demo.py`](NRCell_demo.py) | 构造 PCI 42、30 kHz、载波起点 CRB 10、BWP 起点 CRB 20/宽 24 RB 的配置；显示 SFN 1023 最后一个时隙向下一帧推进 | [`NRCell_config.json`](NRCell_config.json)，保存推进前配置 |
| [`plot_NRCell.py`](plot_NRCell.py) | 绘制帧时隙和 Point A/载波/BWP 坐标 | [`NRCell_overview.png`](NRCell_overview.png)、[`NRCell_overview.svg`](NRCell_overview.svg) |
| [`plot_NRCell_timing.py`](plot_NRCell_timing.py) | 绘制逐符号 CP、60 kHz 精确时隙长度与 FFT 切换 | [`NRCell_timing.png`](NRCell_timing.png)、[`NRCell_timing.svg`](NRCell_timing.svg) |
| [`export_NRCell_reference.m`](export_NRCell_reference.m) | MATLAB 5G Toolbox 独立生成 78 组载波/OFDM 配置 | [`NRCell_reference.json`](NRCell_reference.json) |

```powershell
.venv\Scripts\python examples/cell/NRCell_demo.py
.venv\Scripts\python examples/cell/plot_NRCell.py
.venv\Scripts\python examples/cell/plot_NRCell_timing.py
matlab -batch "addpath('examples/cell'); export_NRCell_reference;"
.venv\Scripts\python -m pytest --require-matlab --cov=cell --cov=grid --cov=diagnostics --cov=srs --cov=common --cov-branch --cov-report=term-missing --cov-fail-under=100
```

只有重新生成 MATLAB 参考时才需要 MATLAB 和 5G Toolbox。导出函数可选输入 `outputFile` 为其他目标文件路径；不传参数时使用上表的同级输出。函数使用 UTF-8 写 JSON，无返回值；无法打开目标文件时中止并报错。调用者应确保自定义输出的父目录存在。

## 调用路径与类变量日志

每个示例在创建主要 NRCell 对象后调用 `dump_state`，完整输出配置字段、常量及所有只读属性，CP/符号数组不截断。时序绘图示例分别输出 30 kHz 和 60 kHz 的具名对象，批量绘制 FFT 曲线的临时对象只记录构造器及后续调用，避免反复输出大量完整快照。

```powershell
# 默认：终端显示完整变量和摘要，文件保存所有调用路径。
.venv\Scripts\python examples/cell/NRCell_demo.py
# 终端也显示调用路径：
$env:NR_LOG_LEVEL = "DEBUG"
.venv\Scripts\python examples/cell/NRCell_demo.py
Remove-Item Env:\NR_LOG_LEVEL
```

调用链覆盖当前线程的 `src/` 源码和当前示例，不记录 Matplotlib 等第三方内部函数。日志中的 elapsed_ms 包含诊断开销，不能用来作为算法性能基准。日志为 UTF-8、UTC 时间戳；`*.log` 已被 Git 忽略。完整 API、各个变量和限制见[ExampleLogger 类文档](../../src/diagnostics/ExampleLogger.md)。MATLAB 入口保持独立，不由 Python profiler 跟踪。

## 配置 JSON

`NRCell_config.json` 由 Python 演示生成，是一个完整的 `NRCell.to_dict()` 结果，包含十二个初始化字段，包括 TDD、4 根发送天线、2 根接收天线。各字段单位、范围与规范依据见[类文档第 2 节](../../src/cell/NRCell.md)。文件没有嵌入派生属性；重建时重新计算这些属性。

```python
import json
from pathlib import Path
from cell import NRCell

# 以下路径以项目根目录为当前工作目录。
config = json.loads(Path("examples/cell/NRCell_config.json").read_text(encoding="utf-8"))
cell = NRCell(**config)
assert (cell.n_frame, cell.n_slot) == (1023, 19)
assert cell.prb_to_crb(0) == 20
```

## MATLAB 参考 JSON

此表是参考数据结构说明，不是协议原表。规范来源是 TS 38.211 V15.2.0 §4.2、§4.3.2、§4.4.2；详细测试参数表在[验证报告](../../documentation/validation/NRCell_validation.md)。

| 字段 | 含义 |
|---|---|
| `matlab_version` | 真实执行 MATLAB 的版本字符串 |
| `toolbox` | `ver('5g')` 的 Name/Version/Release/Date |
| `generated_at` | MATLAB 写出的 UTC 生成时间，ISO 8601 字符串 |
| `spec_baseline` | 当前数据使用的 R15 基线标识 |
| `fft_policy` | 显式 FFT 策略、Windowing=0、无重采样；避免使用 MATLAB 默认 FFT 策略 |
| `cases` | 6 组 SCS/CP × 13 个载波配置 = 78 组独立输入及期望输出 |
| `cases[].input` | MATLAB 载波对象回读的七个输入字段，转为 Python 初始化字段名；不含 BWP |
| `cases[].expected.symbols_per_slot` | `nrCarrierConfig.SymbolsPerSlot` |
| `cases[].expected.slots_per_subframe` | `nrCarrierConfig.SlotsPerSubframe` |
| `cases[].expected.slots_per_frame` | `nrCarrierConfig.SlotsPerFrame` |
| `cases[].expected.n_subcarriers` | 实际 `nrResourceGrid` 第一维长度 |
| `cases[].expected.grid_symbols` | 实际 `nrResourceGrid` 第二维长度 |
| `cases[].expected.n_fft` / `sample_rate_hz` | 实际 `nrOFDMInfo` 返回的 FFT 点数与每分支采样率 |
| `cases[].expected.tc_per_sample` | 每个采样点对应的 Tc 数，按固定 Tc 与 MATLAB 采样率换算 |
| `cases[].expected.cp_lengths_samples` / `symbol_lengths_samples` | MATLAB 的完整子帧 CP / 含 CP 总采样点数向量 |
| `cases[].expected.cp_lengths_tc` / `symbol_lengths_tc` | MATLAB 采样点向量换算为 Tc 数 |
| `cases[].expected.symbol_start_samples` | 从 MATLAB 逐符号采样数累加的起点向量 |
| `cases[].expected.slot_cp_lengths_samples` / `slot_symbol_lengths_samples` | 按当前 NSlot 切片的时隙内向量 |
| `cases[].expected.slot_start_sample` / `samples_per_slot` | 当前时隙起点及其总采样点数 |
| `cases[].expected.samples_per_subframe` / `samples_per_frame` | 完整子帧/帧采样点数 |

Python 测试逐组检查 19 个输出字段（包含数组），展开为 34398 个整数结果，误差容限为 0。`NRCell_config.json` 是演示输入，`NRCell_reference.json` 是 MATLAB 独立期望值；不能用前者或 Python 计算结果覆盖后者。双工模式和物理天线数量不属于 nrCarrierConfig，不以端口数冒充物理天线数量进行验证。

## 逐符号时序文件

[`NRCell_timing.json`](NRCell_timing.json) 由 `NRCell_demo.py` 生成，包含配置、Tc/Ts/KAPPA、FFT/采样率/每采样点 Tc 数、帧/子帧/当前时隙采样数、完整子帧的 CP/符号/起点数组，以及 `current_slot_symbols` 中的当前时隙逐符号信息。字段名与同名类属性一致；数组作用范围和单位见[类文档第 4.2 节](../../src/cell/NRCell.md)。

[`NRCell_timing.csv`](NRCell_timing.csv) 是同一演示当前时隙的 14 行符号信息，列名与 `symbol_timing` 返回字段一致；使用 UTF-8 BOM 方便表格软件读取。`*_tc` 单位为 Tc，`*_samples` 为采样点；两种起点都相对当前子帧，不是相对 SFN 0。读取 JSON 后，各初始化参数仍通过 `NRCell(**data['config'])` 重建。

## 图片含义与验证边界

![NRCell 时频结构](NRCell_overview.png)

上半部分为 30 kHz normal CP 的 10 ms 帧、10 个子帧、20 个时隙。下半部分使用半开 CRB 区间表示载波 `[10,62)` 与活动 BWP `[20,44)`，对应 BWP 内 PRB `[0,24)`。图中的平均时间结构与名义网格带宽分别依据 TS 38.211 V15.2.0 §4.3.1/§4.3.2 与 §4.4.2/§4.4.4/§4.4.5，不表示精确 CP 波形或 RF 信道保护带。

PNG 便于预览，SVG 便于缩放。修改绘图配置后重新运行脚本，避免手工修改图片导致图和代码不一致。
