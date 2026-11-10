# PUSCH首版时域收发示例

```powershell
.venv\Scripts\python -X utf8 examples/pusch/NRPUSCH_demo.py
.venv\Scripts\python -X utf8 examples/pusch/compare_NRPUSCH_reference.py
```

[NRPUSCH_demo.py](NRPUSCH_demo.py)：256位传输块、目标码率0.5、RV0、4RB、符号1起始/长度12、16QAM、单层CP-OFDM、Type-A/Type-1单符号DMRS。数据和DMRS进入NROFDM得到实际时域信号，经两Rx复增益、延迟2采样点、CFO731Hz/初相0.23rad、整slot SNR25dB加噪后接收。已知同步补偿，DMRS估计/MRC、QAM软解映射、UL-SCH反速率匹配/LDPC/CRC，输出比特与CRC及收敛状态。

`main(log,plot_config=None)`：log为ExampleLogger；plot_config为可选NRPlotConfig，默认enabled=True/channel=PUSCH，传NRPlotConfig(enabled=False)关闭。返回接收机结果dict。绘图包含编码位、QAM、网格、OFDM各步骤、信道输出、信道估计、均衡星座和软值，只显示、不保存图片或数值产物；日志按项目约定本地生成并Git忽略。该例是显式给定TBS/目标码率，不包含MCS/TBS调度器。

| 文件 | 用途 |
|---|---|
| [export_NRPUSCH_reference.m](export_NRPUSCH_reference.m) | 实际MATLAB 5G Toolbox导出32个编码/网格/时域案例 |
| [NRPUSCH_reference.json](NRPUSCH_reference.json) | 实际环境、配置、输入TB、编码位、网格、两Rx时域波形 |
| [compare_NRPUSCH_reference.py](compare_NRPUSCH_reference.py) | compare(write_report=True)比较编码/波形/解码并写摘要，False不写；命令行只打印精简结果 |
| [NRPUSCH_comparison.json](NRPUSCH_comparison.json) | 比较结果、误差、CRC/收敛及SHA256 |

独立UL-SCH参考位于examples/common/export_NRULSCHCode_reference.m、NRULSCHCode_reference.json、compare_NRULSCHCode_reference.py及NRULSCHCode_comparison.json，包含CRC24A的4000位单码块案例。

[资源/序列](../../src/pusch/NRPUSCH.md)、[发射机](../../src/pusch/NRPUSCHTransmitter.md)、[接收机](../../src/pusch/NRPUSCHReceiver.md)、[公共UL-SCH](../../src/common/NRULSCHCode.md)、[验证边界](../../documentation/validation/NRPUSCH_validation.md)。

## 1～4层与完整DMRS示例

运行 `.venv\Scripts\python -X utf8 examples/pusch/NRPUSCH_mimo_demo.py`：4层、4Tx/4Rx、Type2双符号、端口(1,7,4,10)、附加位置1、16QAM/256位TB。每层OFDM经非对角4×4有效信道混合，再加2采样点延迟、731Hz频偏、0.23rad初相和25dB SNR噪声。接收机只拿Rx波形，经同步补偿、DMRS联合LS/ZF和UL-SCH恢复；图例Layer0～3表示均衡层。main的plot_config可关闭绘图，图片只显示、不保存。

| 文件 | 用途 |
|---|---|
| [NRPUSCH_mimo_demo.py](NRPUSCH_mimo_demo.py) | 4层带噪时域链路；main(log,plot_config=None)返回接收结果 |
| [export_NRPUSCH_mimo_reference.m](export_NRPUSCH_mimo_reference.m) | MATLAB R2024a/5G Toolbox24.1实际导出64例 |
| [NRPUSCH_mimo_reference.json](NRPUSCH_mimo_reference.json) | 完整配置、输入位、编码位、端口、网格、复信道和混合Rx时域向量 |
| [compare_NRPUSCH_mimo_reference.py](compare_NRPUSCH_mimo_reference.py) | compare(write_report=True)比较并生成摘要；False仅比较 |
| [NRPUSCH_mimo_comparison.json](NRPUSCH_mimo_comparison.json) | 网格/波形/信道误差、CRC、均衡状态和SHA256 |

运行比较：`.venv\Scripts\python -X utf8 examples/pusch/compare_NRPUSCH_mimo_reference.py`。原单层示例保持兼容；当前单层也使用联合LS/ZF。详见[多层验证与边界](../../documentation/validation/NRPUSCH_mimo_validation.md)。不含动态TPMI预编码、DFT-s-OFDM或UCI复用。

## 100MHz / 30kHz测试

- [NRPUSCH_100MHz_30kHz_demo.py](NRPUSCH_100MHz_30kHz_demo.py)：PRB0～272，12符号，1024bit TB，单层QPSK。

统一使用FR1 273PRB/4096FFT/122.88MS/s；run_case(plot_config=None)关闭绘图，直接运行脚本默认显示。结果包含passed、公共元信息、resource、sent及result；图片不保存。每例独立MATLAB参考/比较文件同目录，名称为<类名>_100MHz_30kHz_reference.json和_comparison.json。

共同入口：[MATLAB导出](../common/export_NR100MHz_30kHz_reference.m)、[独立比较](../common/compare_NR100MHz_30kHz_reference.py)、[用例矩阵及边界](../../documentation/validation/NR100MHz_30kHz_validation.md)。

- [NRPUSCH新手导读](../../src/pusch/NRPUSCH.md)：生成步骤、时频位置、配置差异、接收算法与图例。

文档配图：[NRPUSCH_documentation.png](NRPUSCH_documentation.png)。由[公共绘图脚本](../common/plot_NRChannel_documentation.py)生成；默认只显示，显式`--save`才导出文档PNG。
