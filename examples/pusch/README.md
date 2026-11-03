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
