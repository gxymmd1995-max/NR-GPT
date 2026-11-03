# NRPlotConfig：阶段绘图开关与显示配置

[源码](NRPlotConfig.py)是冻结slots dataclass，集中控制是否绘图和选择哪些处理阶段。**图片只显示，不保存PNG/SVG等文件**，没有output_dir或save字段。数值JSON/NPZ仍由原示例按既有约定保存，与图片显示独立。

## 每个字段

| 字段 | 作用、范围与示例 | 单位/维度 |
|---|---|---|
| enabled=False | 严格bool；False完全关闭阶段记录与图窗；True允许选中的阶段显示 | 布尔标量 |
| stages=None | None表示全部阶段；tuple字符串表示fnmatch通配符；空tuple表示不选任何阶段 | 字符串元组；例如('case0.tx.*','case0.rx.*') |
| max_points=2000 | 每条波形/序列最多显示的点数，Python int≥16；仅显示抽样，不修改算法输入/输出 | 点数标量 |
| panels_per_figure=6 | 每个图窗最多阶段面板，Python int1..9；自动分页 | 面板计数标量 |
| max_branches=4 | 波形/序列最多显示的首几个分支，Python int≥1；图中标注实际shape和选择范围 | 分支计数标量 |
| channel='PUCCH' | 非空物理信道标签，显示时用grid.channel_color取得统一颜色 | 字符串标量 |

本配置没有其他属性、常量或随机状态。自动__init__调用__post_init__进行类型/范围校验，错误TypeError或ValueError；未知信道名的颜色错误在实际显示时由channel_color报告。None/stages只控制选择，不改变资源配置或HARQ/SR候选数。

## 阶段选择

独立收发类的阶段名是tx.*和rx.*；完整示例加case0..case3前缀。因此：

```python
from diagnostics import NRPlotConfig

no_plot=NRPlotConfig(enabled=False)
first_case=NRPlotConfig(enabled=True,stages=('case0.*',))
receive_only=NRPlotConfig(enabled=True,stages=('*.rx.*',))
all_stages=NRPlotConfig(enabled=True,stages=None)
```

PUCCH示例默认只显示case0的28个阶段，分5个图窗；stages=None显示全部四类UCI案例。修改[NRPUCCH0_demo.py](../../examples/pucch/NRPUCCH0_demo.py)入口的plot_config字段即可。关掉enabled不导入Matplotlib、不建图窗；不删除之前已有的历史图片。

Matplotlib为可选绘图依赖，运行图窗需要`pip install -e ".[plots]"`和可交互后端。无GUI环境可将[NRStagePlotter](NRStagePlotter.md)的Figure嵌入现有前端或在内存渲染；不必把图片写到磁盘。
