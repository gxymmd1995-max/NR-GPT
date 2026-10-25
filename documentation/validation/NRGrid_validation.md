# NRGrid 验证记录

验证日期：2026-10-25（Asia/Shanghai）。本记录证明本地执行结果；远端提交和 CI 状态以 GitHub 实际记录为准，不能将本地通过视为远端 CI 已运行。

## 实际环境与范围

- Python 3.14.0 / Windows，NumPy 2.5.4，pytest 9.1.1。
- MATLAB R2024a 24.1.0.2537033，5G Toolbox 24.1。
- NRGrid 核心包含 38 项单元测试与 1 项 MATLAB 对比入口，配色模块另有 21 项单元测试，合计 60 项；全部通过，grid 模块源码行和分支覆盖率均为 100%。本节保留网格/配色完成时的191项全项目基线；新增SRS及公共序列后最新回归325项，见 [NRSRS验证](NRSRS_validation.md)。
- MATLAB 入口内部读取 18 个配置，共映射 2736 个 RE；这些不是 pytest 收集的 2736 项独立测试。

## 规范与 MATLAB 依据

本表是追溯索引，不是规范原表。

| 内容 | 原文依据 |
|---|---|
| 时隙符号数量 | TS 38.211 V15.2.0 §4.3.2 表 4.3.2-1/-2 |
| 逻辑端口、RE、资源网格 | 同上 §4.4.1/§4.4.2/§4.4.3 |
| 每 RB 12 子载波、CRB/PRB/BWP 关系 | 同上 §4.4.4.1/3/4、§4.4.5 |
| 复数数组尺寸 | MATLAB 实际 nrResourceGrid 结果 |
| 一基线性索引与轴转换 | MATLAB 原生 sub2ind、列主序，不属于 3GPP 原公式 |
| 占用标签、零值预留、原子写入和冲突策略 | 项目软件规则，另外通过单元测试验证 |

原文定义资源网格的子帧尺寸；本类承载单时隙切片。端口数量为局部逻辑轴，不自动等于物理天线数量，当前不验证天线预编码。

## 独立参考生成

生成脚本：[export_NRGrid_reference.m](../../examples/grid/export_NRGrid_reference.m)。实际输出：[NRGrid_reference.json](../../examples/grid/NRGrid_reference.json)。Python 比对：[test_NRGrid_matlab.py](../../tests/matlab/test_NRGrid_matlab.py)。

MATLAB 独立创建 nrCarrierConfig、调用 nrResourceGrid，依据 CRB/BWP 原文关系生成三元坐标并调用 sub2ind 写入复数值，再提取值、计算全网格和/位置加权和。软件占用 mask 单独记录零值映射与预留位置。生成程序不调用 Python，也不接收 Python 计算结果作为真值。

以下为项目测试参数矩阵，不是原文表；SCS/CP 依据 §4.2 表 4.2-1。

| 维度 | 覆盖 |
|---|---|
| SCS / CP | 15/30/60/120/240 kHz normal，60 kHz extended，共 6 组 |
| 载波宽度 / 端口 | 1 RB / 1 端口、24 RB / 2 端口、52 RB / 4 端口，共 3 组 |
| 载波起点 | CRB 10 |
| BWP | 1 RB 情形 CRB 10 起、宽 1；其他情形 CRB 12 起、宽 4 |
| 时域位置 | 每时隙首、末符号；额外符号 1 预留 |
| 数值 | 第一个映射 RE 为零，其余为 1/16、1/32 的二进制精确分数组合 |

比较形状、BWP 坐标、线性索引、提取顺序、MATLAB 轴、占用/非零/总数及所有值的和/位置加权和，容差为 0。没有将标签占用规则当作 MATLAB Toolbox 的内置功能。

## 单元测试与演示

单元测试覆盖普通/扩展 CP、配置只读性、非法端口/选择/坐标/标签、uint64 大坐标边界、标量广播/向量映射、重复读取、写入重复拒绝、零值占用、预留、显式覆盖、失败不部分写入、空选择、定向及整体清理、所有外部数组副本隔离及 MATLAB 列主序位置。

实际运行 [NRGrid_demo.py](../../examples/grid/NRGrid_demo.py) 生成同级 NPZ、JSON、PNG/SVG 和调用日志。演示总计 2016 个 RE，其中 481 已占用（含 96 个预留和 1 个零值映射）。图中的标签不是具体物理信道。

```powershell
matlab -batch "addpath('examples/grid'); export_NRGrid_reference;"
.venv\Scripts\python -m pytest --require-matlab --cov=cell --cov=grid --cov=diagnostics --cov=srs --cov=common --cov-branch --cov-report=term-missing --cov-fail-under=100
.venv\Scripts\python examples/grid/NRGrid_demo.py
```

验证不包括具体信道的真实序列、OFDM 调制、信道估计、误码率、跨时隙或混合 numerology。后续 SSB、PDSCH 等需各自补充独立 MATLAB 向量。

## 信道配色验证

统一色表为 18 个已知绘图类别分配互不相同的 HEX 颜色，物理信道和参考信号使用固定颜色，未知类别使用灰色，FREE 使用近白。21 项测试检查唯一性、只读色表、别名与 UE 后缀、类别排序、数组不变性及非法输入。真实运行色卡和网格示例并检查 PNG/SVG；JSON 与源色表一致。颜色属于软件展示功能，不重新生成或伪造 MATLAB 信道向量。见[配色说明](../../src/grid/channel_colors.md)。
