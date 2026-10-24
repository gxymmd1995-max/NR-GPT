# NR-GPT：NR Release 15 Python 物理层仿真

以 3GPP R15 为基线的链路级仿真平台。当前已实现 **NRCell 小区配置类**，其他物理信道按计划逐步实现。

## 快速开始

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev,plots]"
.venv\Scripts\python examples/cell/NRCell_demo.py
.venv\Scripts\python -m pytest --require-matlab --cov=cell --cov=diagnostics --cov-branch --cov-report=term-missing --cov-fail-under=100
.venv\Scripts\python examples/cell/plot_NRCell.py
.venv\Scripts\python examples/cell/plot_NRCell_timing.py
```

`--require-matlab` 要求仓库中存在实际 MATLAB 生成的参考向量；测试本身不需要 MATLAB 许可证。重新生成向量需要本机 MATLAB 5G Toolbox。

```python
from cell import NRCell

cell = NRCell(n_cell_id=42, subcarrier_spacing_khz=30,
              n_start_grid=10, bwp_start=20, bwp_size=24,
              duplex_mode="TDD", n_tx_antennas=4, n_rx_antennas=2)
print(cell.slots_per_frame)   # 20
print(cell.prb_to_crb(0))     # 20，BWP 起点相对 CRB 0
print(cell.n_fft, cell.sample_rate_hz, cell.tc_per_sample)  # 1024、30720000、64
print(cell.symbol_timing(0))  # 当前时隙首符号的 CP/有效/总长度：Tc 与采样点
```

## 目录

```text
documentation/
  protocols/             协议原文、协议译文
  planning/              开发计划
  validation/            验证结果说明
src/cell/
  __init__.py            模块导出
  NRCell.py              小区类源码
  NRCell.md              对应类的详细说明
examples/cell/
  NRCell_demo.py         小区示例，输出 NRCell_config.json
  plot_NRCell.py         绘图脚本，输出同级 PNG/SVG
  plot_NRCell_timing.py  FFT、CP、精确时隙时序图
  export_NRCell_reference.m  MATLAB 参考生成脚本
  NRCell_reference.json  MATLAB 实测参考数据
  NRCell_timing.json     子帧时序与当前时隙明细
  NRCell_timing.csv      当前时隙逐符号 Tc / 采样点数
tests/unit/              每个类的单元测试
tests/matlab/            MATLAB 独立参考对比测试
src/diagnostics/         ExampleLogger.py 与同级类说明：日志、调用路径和变量快照
```

- [NRCell：变量、方法、公式与示例](src/cell/NRCell.md)
- [示例、生成文件及 MATLAB 数据格式](examples/cell/README.md)
- [工程架构与命名约定](documentation/architecture.md)
- [开发计划](documentation/planning/NR_R15_物理层仿真平台开发计划.md)
- [规范基线与校验值](documentation/spec_manifest.md)
- [测试与 MATLAB 对比](documentation/validation/NRCell_validation.md)
- [后续模块进度](documentation/feature_matrix.md)
- [本次一致性检查记录](documentation/validation/project_audit.md)
- [日志类、参数和使用方法](src/diagnostics/ExampleLogger.md)

![NRCell 时频结构](examples/cell/NRCell_overview.png)

`pip install -e .` 会生成 `src/nr_r15_phy.egg-info/`，用于记录包名、版本、依赖及安装文件清单。它不是源码，已被 Git 忽略，安装后可以删除；再次安装可能重新生成。类说明随源码存放，示例的配置中间文件、MATLAB 输出和图片都与示例脚本同级。

## 当前边界

NRCell 表示单方向、单 numerology 载波和一个活动 BWP 的配置切片。没有实现完整 gNB、RF 频段组合、TDD 时隙格式、多 BWP 切换或物理信道收发。240 kHz 作为 R15 numerology 可表示，不代表所有数据信道支持该 SCS。

支持 TDD/FDD 模式元数据、物理收发天线数、固定 Tc/Ts、逐符号 CP 与精确采样时序。FFT 根据每符号频域 RE 数（子载波数）取能容纳它的最小 2 的幂，并以 128 为下限；它是平台约定，不是协议强制值。Tc/Ts 固定，实际采样间隔由 FFT×SCS 决定，三者不能混用。

规范表、公式和代码均标明来源；新类需同时提供说明和单元测试，具体物理信道需增加 MATLAB 比对。当前 MATLAB 验证载波尺寸、FFT、采样率、完整子帧及当前时隙的逐符号时序；BWP 坐标、双工/天线元数据和状态转换由独立单元测试检查。

## 许可证

本项目原创代码采用[个人非商业使用许可与商业授权条款](LICENSE)：个人以自身学习、研究和兴趣为目的的非商业使用免费；商业使用须提前取得书面授权，并按双方约定付费。企业内部研发、评估、培训、客户项目、产品集成和收费服务均属于商业使用，不以是否已经盈利为前提。商业授权请联系仓库所有者，价格与授权范围另行约定。

这是自定义的源码可见许可，包含商业使用限制，不属于 [OSI 开源定义](https://opensource.org/osd)下的开源许可证。协议文档和第三方材料保留各自版权与许可；新条款不追溯撤销已合法取得的旧版本授权。

`.coverage` 是 pytest-cov/coverage.py 运行时生成的覆盖率数据库，记录被测试执行的代码行与分支，不是仿真数据或源码。可以删除，下一次使用 `--cov` 测试时会重新生成；Git 已忽略此文件。

## 示例日志

直接运行三个 Python 示例会在 `examples/cell/` 同级生成 `NRCell_demo.log`、`plot_NRCell.log`、`plot_NRCell_timing.log`，记录函数调用路径、参数、出口值、耗时和完整 NRCell 变量快照（12 字段、8 常量、35 属性）。终端默认显示 INFO 摘要与变量，文件包含 DEBUG 调用详情；设置 `$env:NR_LOG_LEVEL = "DEBUG"` 可在终端同时查看调用链。日志 UTF-8、时间戳 UTC、每次运行覆盖，已被 Git 忽略。详见[日志类文档](src/diagnostics/ExampleLogger.md)。
