# SRS 示例与实际参考

## 接收端、噪声和RI/TPMI

新增 [NRSRSReceiver](../../src/srs/NRSRSReceiver.md)接收已完成OFDM解调的频域采样，联合解扩已知用户SRS；上行RI/TPMI通过 [NRUplinkCodebook](../../src/common/NRUplinkCodebook.md)搜索固定R15码本。

```powershell
.venv\Scripts\python -X utf8 examples/srs/NRSRSReceiver_demo.py
.venv\Scripts\python -X utf8 examples/srs/compare_NRSRSReceiver_reference.py
```

| 文件 | 用途/结构（项目说明表） |
|---|---|
| [NRSRSReceiver_demo.py](NRSRSReceiver_demo.py) | main(log)模拟3用户、4Rx、有限FIR、已知多径、不同PRB噪声；json_value(value)将复数数组转real/imag、NaN转null；保存全部结果及对照图 |
| [NRSRSReceiver_summary.json](NRSRSReceiver_summary.json) | cell/receiver/resources完整配置、true_delay_samples、理论噪声方差、随机种子和result；结果字段详见类文档，复数为real/imag两个同形列表 |
| [NRSRSReceiver_data.npz](NRSRSReceiver_data.npz) | rx_grid/noise_grid:[4,14,288]；noise_mask:[14,288]；true_noise_variance_per_rb:[24]；每用户true_cir/estimated_cir:[4,P,8]、estimated_channel:[4,P,288]、tx_grid:[P,14,288] |
| [NRSRSReceiver_overview.png](NRSRSReceiver_overview.png) / [SVG](NRSRSReceiver_overview.svg) | 实际接收功率、PRB与宽带噪声、各用户时延谱、RI/TPMI表；图中功率是归一化值，非RF dBm |
| [NRSRSReceiver_cs_windows.png](NRSRSReceiver_cs_windows.png) / [SVG](NRSRSReceiver_cs_windows.svg) | 诊断图：去公共基序列后的IFFT坐标与预期CS窗；UE0/UE1同组，UE2使用不同序列/梳齿单独展示。阴影为8采样点因果窗，虚线是真实相对延迟叠加后的位置 |
| [export_NRSRSReceiver_reference.m](export_NRSRSReceiver_reference.m) | 独立nrSRS/nrSRSIndices/nrResourceGrid生成参考，原生MATLAB联合LS/噪声/时延，nrPUSCHCodebook逐候选评分；outputFile可选 |
| [NRSRSReceiver_reference.json](NRSRSReceiver_reference.json) | 24组真实MATLAB接收输入/期望，32个用户结果，含MATLAB/Toolbox/UTC/基线；约15MB全量复数输入与信道，不调用Python生成 |
| [compare_NRSRSReceiver_reference.py](compare_NRSRSReceiver_reference.py) | compare(log)从真实参考重新计算Python结果，验证逐用户RI/TPMI/时延及复数CIR/H、噪声；同时验证72个码本矩阵 |
| [NRSRSReceiver_comparison.json](NRSRSReceiver_comparison.json) | 比较状态、最大误差、逐组决策、相关参考与源码SHA256；这是Python验证结果，不是MATLAB原始输出 |

接收演示采用0.002复噪声功率/RE，PRB12..15增加到0.03；宽带测得约0.006651。三个用户最强径分别为3、6、1样点；RI/TPMI分别为2/0、1/5、1/0。时延相对FFT窗口；同时输出首径、平均延迟和RMS扩展，不能将最强径直接等同于绝对传播距离。UE0/UE1共享RE，通过已知循环移位和有限延迟模型联合分离。

循环移位配置并非三个UE各不相同：UE0端口CS=0/4、UE1=2/6，UE2的CS=0但使用comb4/offset1/sequence93，与前两者不同组。overview中的CIR已去CS，按各用户相对时延叠画；cs_windows图保留公共谱坐标。Nfft512/comb2时IFFT周期256采样点，UE0两个窗原点0/128，UE1为192/64；对应真实峰3/131及198/70。UE2单独128点周期，窗原点0、峰1。JSON的cyclic_shift_windows逐端口保存这些诊断坐标，不改变接收机或RI/TPMI算法。

MATLAB JSON的rx向量对应Python`[Rx,L,K]`的C-order；cir对应`[Rx,P,D]`，channel对应`[Rx,P,K]`。input.resources单用户可能编码为对象，多用户为列表。expected.narrow_per_rx按`[Rx,24]`恢复，未测PRB以null表示；完整字段及误差规则见 [接收验证](../../documentation/validation/NRSRSReceiver_validation.md)。

```powershell
& 'E:\Program Files\MATLAB\R2024a\bin\matlab.exe' -batch "addpath('examples/common'); addpath('examples/srs'); export_NRUplinkCodebook_reference; export_NRSRSReceiver_reference;"
.venv\Scripts\python -X utf8 -m pytest tests/matlab/test_NRSRSReceiver_matlab.py tests/matlab/test_NRUplinkCodebook_matlab.py --require-matlab
```

后文保留发送端示例说明。

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


接收示例增加每UE SNR、RSSI/RSRP及dB值，JSON还保留每Rx功率、RSSI测量带宽。概览图和日志显示三项指标。噪声统一调用NRChannel按SNR生成：本频域示例逐PRB平铺Rx/RE，配置12 dB（PRB12..15为0 dB）以演示有色噪声；每PRB目标SNR是整块RE平均口径，接收机用户SNR是实际SRS RE上的用户分离功率口径。[指标定义](../../src/srs/NRSRSReceiver.md)。
