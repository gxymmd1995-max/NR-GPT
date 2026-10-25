# SRS 示例与实际参考

使用 NRCell 配置小区，NRSRS 合成参考信号，NRGrid 管理实际 RE 并显示频域位置；类的每个参数/方法与协议公式见 [NRSRS.md](../../src/srs/NRSRS.md)。

```powershell
.venv\Scripts\python -X utf8 examples/srs/NRSRS_demo.py
.venv\Scripts\python -X utf8 examples/srs/compare_NRSRS_reference.py
.venv\Scripts\python -X utf8 -m pytest tests/unit/test_NRSRS.py tests/matlab/test_NRSRS_matlab.py --require-matlab
```

示例启用 ExampleLogger，同目录日志记录函数调用链与参数/返回；NRSRS_demo 还打印 cell/srs/grid 的全部变量。`NR_LOG_LEVEL=WARNING` 可以减小终端输出，文件仍保存 DEBUG 详情；日志较大，均由 Git 忽略。

以下是项目文件说明表，不是协议参数原表。

| 文件 | 用途 / 数据格式 |
|---|---|
| [NRSRS_demo.py](NRSRS_demo.py) | `main(log)` 创建小区/信号/网格，保存快照和产物；`plot_allocation(srs,grid,output)` 画完整载波与 comb 细节；`plot_hopping(srs,output)` 由连续8个真实 NRGrid 提取占用并返回 [absolute_slot,p,l,k] |
| [NRSRS_summary.json](NRSRS_summary.json) | input=完整19字段；hopping_view_input=另一个重复因子配置；matlab_srs_config=适配器配置；grid=NRGrid摘要；sequence_parameters=u/v/alpha；mapped_re_count、能量与许可边界 |
| [NRSRS_data.npz](NRSRS_data.npz) | indices:(576,3) int64 [p,l,k]；raw_symbols:(144,4) complex128；data:(4,14,624) complex128；owners:同形U64；hopping_indices:(4608,4) int64 [absolute_slot,p,l,k] |
| [NRSRS_frequency_positions.csv](NRSRS_frequency_positions.csv) | 当前时隙每个 RE 的本地端口、协议端口、符号、载波子载波、CRB、RB内子载波、相对载波中心 Hz、相对 Point A Hz；公式见类文档 S10/S11 |
| [NRSRS_allocation.png](NRSRS_allocation.png) / [SVG](NRSRS_allocation.svg) | 四个逻辑端口的实际 SRS 网格及每4子载波占1个的 comb4 细节，采用统一棕色 |
| [NRSRS_hopping.png](NRSRS_hopping.png) / [SVG](NRSRS_hopping.svg) | 同一配置将 repetition 改为4，当前 slot 内同频，跨 slot 交替两个12RB区间；展示端口0，完整四端口坐标保存在 NPZ |
| [export_NRSRS_reference.m](export_NRSRS_reference.m) | MATLAB 独立生成函数，outputFile 可选，默认同目录 NRSRS_reference.json；不执行或读取 Python 算法 |
| [NRSRS_reference.json](NRSRS_reference.json) | 832组真实 MATLAB 输入及全部复数/坐标，包含环境和 UTC 时间；约19MB，保留全向量而非少量抽样点 |
| [compare_NRSRS_reference.py](compare_NRSRS_reference.py) | `compare(log)` 对实测向量逐点比较 Python 序列/索引/映射值，失败即抛错，成功返回并保存报告；入口启用调用链日志 |
| [NRSRS_comparison.json](NRSRS_comparison.json) | Python 比较报告：MATLAB参考与实现 SHA256、环境、总组数/值数、最大误差、逐组结果；不是 MATLAB 原始输出 |

默认示例：30kHz、普通 CP、52RB，载波始于CRB10，BWP为CRB20..43。SRS c_srs=7/b_srs=1，每符号12RB、comb4，4端口、4符号、l_offset=5，频域 shift=10 个载波内RB；当前 slot 写576个RE，beta=1时总能量144。四端口使用相同的上行频域资源，逻辑端口分别存放；物理天线的实际波形和预编码尚未实现。

allocation 图使用 repetition=1，展示时隙内跳频；hopping 图使用 repetition=4，展示时隙间跳频。两者输入都保存在 summary，避免把两种图误解为完全相同配置。所有点都从 NRGrid.occupancy 提取。图中空白符号/子载波只表示这个示例未分配，不代表完整上行调度。

重新生成真实 MATLAB 参考，在根目录执行：

```powershell
& 'E:\Program Files\MATLAB\R2024a\bin\matlab.exe' -batch "addpath('examples/srs'); export_NRSRS_reference;"
.venv\Scripts\python -X utf8 examples/srs/compare_NRSRS_reference.py
.venv\Scripts\python -X utf8 -m pytest tests/matlab/test_NRSRS_matlab.py --require-matlab
```

MATLAB JSON 顶层保存 matlab_version、toolbox、generated_at、spec_baseline、note、cases。每个 case.input 是完整 NRSRS 参数与小区字段；expected 保存 active、indices、sequence_shape、symbols_real/imag、seq_group、n_seq、alpha、sequence_length、k0、frequency_indices、occupied_re_count、grid_energy、grid_weighted_real/imag。复数向量按 MATLAB `symbols(:)` 端口优先扁平化，Python 为 ravel(order="F")；indices 为0起始[p,l,k]。MATLAB 将单元素向量/矩阵编码为标量或一维，比较测试按配置尺寸还原。空序列仍保留 Python 的端口维度。

查看数值：

```python
import numpy as np

with np.load("examples/srs/NRSRS_data.npz") as values:
    print(values["indices"][:4])
    print(values["raw_symbols"][:4])
    print(values["data"].shape)
```
