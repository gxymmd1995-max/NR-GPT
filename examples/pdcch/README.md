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
