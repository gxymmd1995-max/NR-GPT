# 物理信道和参考信号配色

源码：[channel_colors.py](channel_colors.py)；测试：[test_channel_colors.py](../../tests/unit/test_channel_colors.py)。本模块仅提供函数和只读映射，不定义新的类。

## 目的与规则

资源网格按 owner 标签选择固定颜色，而不是按振幅、端口或标签出现顺序随机选色。同一个物理信道在不同图中保持相同颜色，不同已知信道使用不同 HEX 颜色。颜色是本项目的显示约定，**不是 3GPP R15 规定的颜色或物理信道实现**。

SSB 是 SS/PBCH 块，SRS、DM-RS、PT-RS、CSI-RS、PSS/SSS 等包含信号类别；这里将它们共同作为绘图类别，并不混淆协议中的信道/信号分类。PRACH 的颜色只用于图例或以后独立波形展示，不因此将 PRACH 当作普通载波 OFDM 网格处理。

## 常量、别名与颜色

以下是项目软件配色表，没有对应的 3GPP 原表。

| 类别 | HEX | 显示含义 |
|---|---|---|
| `SSB` | `#E69F00` | SS/PBCH 块，橙黄 |
| `PDCCH` | `#0072B2` | 下行控制，蓝 |
| `PDSCH` | `#009E73` | 下行共享数据，绿 |
| `PUSCH` | `#9467BD` | 上行共享数据，紫 |
| `PUCCH` | `#D55E00` | 上行控制，朱红 |
| `PRACH` | `#56B4E9` | 随机接入，天蓝 |
| `SRS` | `#8C564B` | 探测参考信号，棕 |
| `DMRS` | `#F0E442` | 解调参考信号，黄 |
| `PTRS` | `#E377C2` | 相位跟踪参考信号，粉 |
| `CSI_RS` | `#17BECF` | CSI 参考信号，青 |
| `PSS` | `#B8860B` | 主同步，深金 |
| `SSS` | `#BCBD22` | 辅同步，橄榄 |
| `PBCH` | `#FF7F0E` | 广播，橙 |
| `FREE` | `#F8FAFC` | 空闲，近白 |
| `RESERVED` | `#94A3B8` | 软件预留，浅灰 |
| `STREAM_A` | `#3B82F6` | 兼容现有演示流 A |
| `STREAM_B` | `#10B981` | 兼容现有演示流 B |
| `ZERO` | `#EF4444` | 已占用但数值为零的演示 RE |

`CHANNEL_COLORS` 是 MappingProxyType 只读表，18 个已知类别 HEX 互不相同，不能在运行中意外改写。`UNKNOWN_COLOR = "#6B7280"` 是未知类别的灰色，不等于 FREE；多个未知类别保留不同图例名称，但共享灰色。

内部 `_ALIASES` 用于精确别名转换：DM_RS→DMRS、PT_RS→PTRS、SS/PBCH→SSB、SS_PBCH→SSB。`_channel_name` 先裁剪首尾空格、按冒号取类型前缀、转为大写并把连字符改成下划线，因此 DM-RS、PT-RS、CSI-RS 也能识别。空白标签为 FREE；非空但前缀为空的未知标签（如 `:UE0`）仍是未知类别，不会变成 FREE。

## 每个函数

本表是软件 API 表，不是协议原表。

| 函数 | 参数、返回值与异常 |
|---|---|
| `channel_color(owner)` | owner 为字符串标签，返回固定 `#RRGGBB`。例如 `channel_color("PDSCH") == "#009E73"`；非字符串抛 TypeError |
| `encode_owners(owners)` | 输入非空二维/三维 Unicode 字符串数组，返回 `(codes, labels, colors)`；维度/空数组抛 ValueError，非 Unicode dtype（含 object）抛 TypeError |
| `_channel_name(owner)` | 内部归一化函数，返回类别名。以 `PDSCH:UE0` 形式区分实例，同时沿用 PDSCH 颜色；这只是显示归类，不修改原始占用标签 |

`codes` 是与输入同形状的 int64 数组，`labels` 和 `colors` 是 tuple。通过 `labels[codes[p,l,k]]` 可得到某 RE 的类别。已知类别按固定表顺序排列，未知类别按名称排序；图中缺少部分信道时编号可能变化，但该类别的实际 HEX 颜色不变化。输入数组不修改。

`PDSCH:UE0`、`PDSCH:UE1` 会合并为一个 PDSCH 图例；要将参考信号单独着色，应采用 `DMRS:PDSCH` 这样的前缀，而不是 `PDSCH:DMRS`。后者按 PDSCH 显示。不要依靠颜色推导信道参数或生成真实信号。

```python
import numpy as np
from grid import CHANNEL_COLORS, channel_color, encode_owners

assert channel_color("pdsch:UE0") == channel_color("PDSCH:UE1")
assert channel_color("PDCCH") != channel_color("PDSCH")
assert channel_color("DM-RS") == CHANNEL_COLORS["DMRS"]
owners = np.array([["", "PDSCH:UE0", "DMRS:PDSCH", "PUCCH"]])
codes, labels, colors = encode_owners(owners)
assert codes.shape == owners.shape
assert labels[codes[0, 1]] == "PDSCH"
assert colors[codes[0, 3]] == CHANNEL_COLORS["PUCCH"]
```

## 图与产物

现有 NRGrid 绘图已调用 encode_owners，自动根据实际标签生成图例。未知标签会显示为灰色而非被静默当成空闲。新增的配色图示只画色卡，不假造物理信道布局或波形。

```powershell
.venv\Scripts\python examples/grid/plot_NRGrid_channel_colors.py
.venv\Scripts\python examples/grid/NRGrid_demo.py
```

脚本在 `examples/grid/` 同级生成 [PNG](../../examples/grid/NRGrid_channel_colors.png)、[SVG](../../examples/grid/NRGrid_channel_colors.svg)、[JSON 色表](../../examples/grid/NRGrid_channel_colors.json) 和运行日志。日志忽略规则保持不变。

![物理信道配色](../../examples/grid/NRGrid_channel_colors.png)

配色不改变复数值、占用状态、资源冲突规则或 MATLAB 参考数据。测试覆盖已知颜色唯一性、只读性、别名、UE 后缀、未知标签可见性、类别排序稳定、二维/三维数组及非法输入。这是软件展示功能，不要求伪造 MATLAB 信道向量。
