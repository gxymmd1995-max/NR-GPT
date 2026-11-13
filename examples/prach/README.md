# PRACH时域收发与MATLAB参考

新手建议先读[PRACH信号生成、时频位置与配置对照](../../src/prach/NRPRACH.md#新手导读先从一次敲门理解-prach)，再看[发射各阶段图](../../src/prach/NRPRACHTransmitter.md#各阶段图应该看什么)和[接收算法与相关峰](../../src/prach/NRPRACHReceiver.md#从接收数组到前导编号逐步解释)。文档包含采样点时间轴、频域占用图、不同格式/间隔对照和三UE检测窗解释。

运行 `.venv\Scripts\python -X utf8 examples/prach/NRPRACH_demo.py`。

[NRPRACH_demo.py](NRPRACH_demo.py)使用NRCell的52RB/30kHz/2Rx，PRACH A1/15kHz、逻辑根0、NCS=15。三个用户同一时频机会发送前导0/1/2，循环移位分别0/15/30，经3/7/12采样点延迟及不同双Rx复增益叠加，再加入731Hz频偏、0.23rad初相、25dB SNR噪声。接收端不知道发送编号和延迟，在64前导中搜索并恢复三个结果；无RAR/Msg3过程。

`main(log,plot_config=None)`接收ExampleLogger及可选NRPlotConfig，返回接收dict；默认显示绘图，传NRPlotConfig(enabled=False)关闭。图涵盖ZC、DFT、独立PRACH频谱、IFFT、CP/时域叠加、相关曲线和前导分数。图片只显示，不保存；重复tx阶段为逐UE真实结果。日志生成于本目录并Git忽略。若只关注检测可设置stages=('rx.*','channel.*')。

## 对照 13 种 PRACH 格式的时域波形

[NRPRACH_formats_demo.py](NRPRACH_formats_demo.py) 默认运行 16 组。先在上行载波 SCS 为 30 kHz、采样率为 30.72 MS/s 的条件下对照全部 13 种格式，再保持短格式 A1 不变，对照 RA SCS 为 15、30、60、120 kHz 时的周期和 CP。

| 格式族 | 格式 | RA SCS（kHz） | 对应可选的 UL SCS（kHz） |
|---|---|---:|---|
| 长格式 | 0、1、2 | 1.25 | 15、30、60 |
| 长格式 | 3 | 5 | 15、30、60 |
| 短格式 | A1～A3、B1～B4、C0、C2 | 15 或 30 | 15、30、60 |
| 短格式 | A1～A3、B1～B4、C0、C2 | 60 或 120 | 60、120 |

此表按 TS 38.211 V15.2.0 §6.3.3 的原表 6.3.3.1-1、6.3.3.1-2 和 6.3.3.2-1 归纳显式时机示例。载波 SCS 用于建立 `NRCell` 的采样率，PRACH SCS 决定一个有用重复周期。实际部署时还需按频率范围、双工模式和 PRACH Configuration Index 查可用时机。[协议索引](../../documentation/spec_manifest.md)

在仓库根目录运行：

```powershell
# 16 个代表案例，显示图形
.venv\Scripts\python.exe -X utf8 examples/prach/NRPRACH_formats_demo.py
# 长格式 0～3，保持上行载波为 30 kHz
.venv\Scripts\python.exe -X utf8 examples/prach/NRPRACH_formats_demo.py --group long
# 短格式 A1，分别以 60 kHz 或 120 kHz RA SCS 运行
.venv\Scripts\python.exe -X utf8 examples/prach/NRPRACH_formats_demo.py --format A1 --ra-scs 60 --ul-scs 60
.venv\Scripts\python.exe -X utf8 examples/prach/NRPRACH_formats_demo.py --format A1 --ra-scs 120 --ul-scs 120
# 批量执行全部 102 组，只输出数值
.venv\Scripts\python.exe -X utf8 examples/prach/NRPRACH_formats_demo.py --all-pairs --no-plot
```

左图是发射波形的 I 分量，橙色为 CP，虚线分隔有用重复周期，末尾灰区是为延迟仿真添加的 32 个补零样点。右图是接收相关曲线，实线对应发送的前导 7，另一条曲线是每个延迟点上其余 63 个候选中的最高分。每例经 3 样点延迟、731 Hz CFO、0.23 rad 初相及 25 dB SNR 噪声后，在已知 CFO 和初相的条件下搜索全部 64 个候选，期望只在前导 7 的第 3 个样点检出。不同采样率下，3 样点对应的微秒数不同。

终端表给出采样率、PRACH FFT 长度、CP 样点和微秒数、重复次数及活动时长。先对比长格式 0 与 1 的 CP，再对比同为两次重复的短格式 A1 与 B1。短格式采用显式时机起点 0，CP 样点含 §5.3.2 的边界扩展。图只显示，使用 `--no-plot` 可直接检查终端结果。

全部 102 组是 Python 时域演示。真实 MATLAB 比对覆盖范围见下表及[验证报告](../../documentation/validation/NRPRACH_validation.md)。

| 文件 | 用途 |
|---|---|
| [export_NRPRACH_reference.m](export_NRPRACH_reference.m) | 在真实MATLAB R2024a/5G Toolbox24.1生成44个时域案例及32个序列边界案例 |
| [NRPRACH_reference.json](NRPRACH_reference.json) | 环境、配置、逻辑根/前导/NCS、MATLAB序列元信息、复DFT符号和实际CP+活动时域向量 |
| [compare_NRPRACH_reference.py](compare_NRPRACH_reference.py) | compare(write_report=True)写比较报告；False仅比较；比较64候选检测、根/移位、序列和时域波形 |
| [NRPRACH_comparison.json](NRPRACH_comparison.json) | 误差、检测、参数一致性、门限、环境及SHA256 |

导出：MATLAB调用`addpath('examples/prach'); export_NRPRACH_reference`；比较：`.venv\Scripts\python -X utf8 examples/prach/compare_NRPRACH_reference.py`。参考波形保留所选时机的CP及活动周期；MATLAB调度中的其他时机/空子帧不纳入Python显式时机接口，比较时按记录start补零对齐。C2的完整CP周期在Toolbox中被归为网格符号，比较总样点而非机械对齐CP字段。

见[资源文档](../../src/prach/NRPRACH.md)、[发送机](../../src/prach/NRPRACHTransmitter.md)、[接收机](../../src/prach/NRPRACHReceiver.md)和[验证边界](../../documentation/validation/NRPRACH_validation.md)。

## 100MHz / 30kHz测试

- [NRPRACH_100MHz_30kHz_demo.py](NRPRACH_100MHz_30kHz_demo.py)：A1，RA间隔30kHz，频域起点261，前导7。

统一使用FR1 273PRB/4096FFT/122.88MS/s；run_case(plot_config=None)关闭绘图，直接运行脚本默认显示。结果包含passed、公共元信息、resource、sent及result；图片不保存。每例独立MATLAB参考/比较文件同目录，名称为<类名>_100MHz_30kHz_reference.json和_comparison.json。

共同入口：[MATLAB导出](../common/export_NR100MHz_30kHz_reference.m)、[独立比较](../common/compare_NR100MHz_30kHz_reference.py)、[用例矩阵及边界](../../documentation/validation/NR100MHz_30kHz_validation.md)。

文档配图：[NRPRACH_documentation.png](NRPRACH_documentation.png)。由[公共绘图脚本](../common/plot_NRChannel_documentation.py)生成；默认只显示，显式`--save`才导出文档PNG。
