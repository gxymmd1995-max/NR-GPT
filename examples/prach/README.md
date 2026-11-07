# PRACH时域收发与MATLAB参考

运行 `.venv\Scripts\python -X utf8 examples/prach/NRPRACH_demo.py`。

[NRPRACH_demo.py](NRPRACH_demo.py)使用NRCell的52RB/30kHz/2Rx，PRACH A1/15kHz、逻辑根0、NCS=15。三个用户同一时频机会发送前导0/1/2，循环移位分别0/15/30，经3/7/12采样点延迟及不同双Rx复增益叠加，再加入731Hz频偏、0.23rad初相、25dB SNR噪声。接收端不知道发送编号和延迟，在64前导中搜索并恢复三个结果；无RAR/Msg3过程。

`main(log,plot_config=None)`接收ExampleLogger及可选NRPlotConfig，返回接收dict；默认显示绘图，传NRPlotConfig(enabled=False)关闭。图涵盖ZC、DFT、独立PRACH频谱、IFFT、CP/时域叠加、相关曲线和前导分数。图片只显示，不保存；重复tx阶段为逐UE真实结果。日志生成于本目录并Git忽略。若只关注检测可设置stages=('rx.*','channel.*')。

| 文件 | 用途 |
|---|---|
| [export_NRPRACH_reference.m](export_NRPRACH_reference.m) | 在真实MATLAB R2024a/5G Toolbox24.1生成44个时域案例及32个序列边界案例 |
| [NRPRACH_reference.json](NRPRACH_reference.json) | 环境、配置、逻辑根/前导/NCS、MATLAB序列元信息、复DFT符号和实际CP+活动时域向量 |
| [compare_NRPRACH_reference.py](compare_NRPRACH_reference.py) | compare(write_report=True)写比较报告；False仅比较；比较64候选检测、根/移位、序列和时域波形 |
| [NRPRACH_comparison.json](NRPRACH_comparison.json) | 误差、检测、参数一致性、门限、环境及SHA256 |

导出：MATLAB调用`addpath('examples/prach'); export_NRPRACH_reference`；比较：`.venv\Scripts\python -X utf8 examples/prach/compare_NRPRACH_reference.py`。参考波形保留所选时机的CP及活动周期；MATLAB调度中的其他时机/空子帧不纳入Python显式时机接口，比较时按记录start补零对齐。C2的完整CP周期在Toolbox中被归为网格符号，比较总样点而非机械对齐CP字段。

见[资源文档](../../src/prach/NRPRACH.md)、[发送机](../../src/prach/NRPRACHTransmitter.md)、[接收机](../../src/prach/NRPRACHReceiver.md)和[验证边界](../../documentation/validation/NRPRACH_validation.md)。
