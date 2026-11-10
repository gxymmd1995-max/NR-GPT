# SS/PBCH块示例与实际MATLAB参考

```powershell
.venv\Scripts\python -X utf8 examples/ssb/NRSSB_demo.py
.venv\Scripts\python -X utf8 examples/ssb/NRSSB_100MHz_30kHz_demo.py
.venv\Scripts\python -X utf8 examples/ssb/compare_NRSSB_reference.py
```

| 文件 | 用途 |
|---|---|
| [NRSSB_demo.py](NRSSB_demo.py) | main(log,plot_config=None,n_size_grid=24)；双Rx时域闭环，返回接收dict |
| [NRSSB_100MHz_30kHz_demo.py](NRSSB_100MHz_30kHz_demo.py) | 同一main使用273PRB/4096FFT/122.88MS/s；SSB自身占20RB×4符号 |
| [export_NRSSB_reference.m](export_NRSSB_reference.m) | 实际R2024a/5G Toolbox25例，含100MHz案例 |
| [NRSSB_reference.json](NRSSB_reference.json) | 环境、MIB/SFN低位/半帧/索引/PCI/间隔/载波大小、编码位、完整复网格与实际时域波形 |
| [compare_NRSSB_reference.py](compare_NRSSB_reference.py) | compare(write_report=True)比较并写摘要；False只比较 |
| [NRSSB_comparison.json](NRSSB_comparison.json) | 编码精确一致性、网格/波形误差、PCI/索引/MIB/CRC恢复及SHA256 |

默认显示真实PSS/SSS、BCH编码、PBCH星座、资源网格、OFDM变换和接收搜索分数，图片只显示、不保存。main传NRPlotConfig(enabled=False)关闭，或用stages筛选；日志由ExampleLogger放本目录并Git忽略。

演示：PCI1007、Lmax8/索引7/半帧1、SFN低4位6、原始24位测试载荷；位置为载波局部子载波24、slot符号2。实际OFDM波形经双Rx复增益、2采样点时延、731Hz频偏/0.23rad初相、25dB SNR噪声。接收资源刻意使用PCI0/索引0，通过已知时频窗口内PSS/SSS及PBCH DMRS搜索恢复真值，随后SC/CRC恢复MIB和完整SFN678。调用方显式提供同步补偿；不宣称已实现未知时频位置的全频段盲扫或真实MIB调度。

MATLAB：`addpath('examples/ssb');export_NRSSB_reference`。完整比对包括真实MATLAB波形送入Python接收机，未将真实PCI/SSB索引/半帧作为接收标签。真实Case A～E时机调度和MIB语义配置不在本演示范围，原始测试载荷不等于可直接入网的MIB配置。

类文档：[资源](../../src/ssb/NRSSB.md)、[发射机](../../src/ssb/NRSSBTransmitter.md)、[接收机](../../src/ssb/NRSSBReceiver.md)、[公共BCH](../../src/common/NRBCHCode.md)。详见[验证及边界](../../documentation/validation/NRSSB_validation.md)。

- [NRSSB新手导读](../../src/ssb/NRSSB.md)：生成步骤、时频位置、配置差异、接收算法与图例。

文档配图：[NRSSB_documentation.png](NRSSB_documentation.png)。由[公共绘图脚本](../common/plot_NRChannel_documentation.py)生成；默认只显示，显式`--save`才导出文档PNG。
