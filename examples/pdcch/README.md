# PDCCH时域收发示例

运行`.venv\Scripts\python -X utf8 examples/pdcch/NRPDCCH_demo.py`。

NRPDCCH_demo.py的main(log,plot_config=None)使用24RB、聚合等级4、REG交织、32位DCI、RNTI4321和ID271。实际OFDM波形经两Rx复增益、2采样点延迟、731Hz频偏/0.23rad初相和25dB SNR噪声，再进行已知同步补偿、DMRS/LS/MRC及Polar/CRC解码。返回接收dict。默认绘图仅显示、不保存；NRPlotConfig(enabled=False)关闭；日志按本目录生成并Git忽略。

| 文件 | 用途 |
|---|---|
| [NRPDCCH_demo.py](NRPDCCH_demo.py) | 单候选带噪时域收发 |
| [export_NRPDCCH_reference.m](export_NRPDCCH_reference.m) | 真实MATLAB导出15例编码、网格及波形 |
| [NRPDCCH_reference.json](NRPDCCH_reference.json) | 环境、输入payload、聚合等级/变体、编码位、复网格/波形；公共固定输入在脚本中 |
| [compare_NRPDCCH_reference.py](compare_NRPDCCH_reference.py) | compare(write_report=True)独立比较并写摘要；False只比较 |
| [NRPDCCH_comparison.json](NRPDCCH_comparison.json) | 误差、编码位/CRC及源码/输入SHA256 |

MATLAB运行`addpath('examples/pdcch');export_NRPDCCH_reference`；比较运行`.venv\Scripts\python -X utf8 examples/pdcch/compare_NRPDCCH_reference.py`。

见[资源](../../src/pdcch/NRPDCCH.md)、[发射机](../../src/pdcch/NRPDCCHTransmitter.md)、[接收机](../../src/pdcch/NRPDCCHReceiver.md)、[DCI编码](../../src/common/NRDCICode.md)、[验证边界](../../documentation/validation/NRPDCCH_validation.md)。

## 100MHz / 30kHz测试

- [NRPDCCH_100MHz_30kHz_demo.py](NRPDCCH_100MHz_30kHz_demo.py)：45个六RB组/270RB CORESET，2符号，AL4显式候选，32bit DCI。

统一使用FR1 273PRB/4096FFT/122.88MS/s；run_case(plot_config=None)关闭绘图，直接运行脚本默认显示。结果包含passed、公共元信息、resource、sent及result；图片不保存。每例独立MATLAB参考/比较文件同目录，名称为<类名>_100MHz_30kHz_reference.json和_comparison.json。

共同入口：[MATLAB导出](../common/export_NR100MHz_30kHz_reference.m)、[独立比较](../common/compare_NR100MHz_30kHz_reference.py)、[用例矩阵及边界](../../documentation/validation/NR100MHz_30kHz_validation.md)。

- [NRPDCCH新手导读](../../src/pdcch/NRPDCCH.md)：生成步骤、时频位置、配置差异、接收算法与图例。

文档配图：[NRPDCCH_documentation.png](NRPDCCH_documentation.png)。由[公共绘图脚本](../common/plot_NRChannel_documentation.py)生成；默认只显示，显式`--save`才导出文档PNG。
