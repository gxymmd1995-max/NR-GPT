# OFDM、逐符号相位与时域信道验证

日期：2026-10-26。固定OFDM/相位基线 **TS38.211 V15.2.0 §5.3.1/§5.4**，TA换算基线 **TS38.213 V15.3.0 §4.2**。CFO/AWGN/有限窗口操作属于工程模型。接口文档：[NROFDM](../../src/common/NROFDM.md)、[NRPhaseRotation](../../src/common/NRPhaseRotation.md)、[NRChannel](../../src/channel/NRChannel.md)。

## 实际独立参考

已实际运行MATLAB24.1.0.2537033(R2024a)、5G Toolbox24.1：

- [OFDM脚本](../../examples/common/export_NROFDM_reference.m)直接调用nrOFDMModulate、nrOFDMDemodulate、nrOFDMInfo，28组调制/逐符号相位，84组接收解调。覆盖15/30/60/120/240kHz普通CP、60kHz扩展CP、slot0/1、1/24RB、1/2分支、f0=0和3500000123Hz、CP比例0/0.5/1。显式Nfft、Windowing0；保存每个时域样点、相位与解调RE。
- 解调输入包含MATLAB独立构造的非OFDM扰动，避免仅测试自调制/自解调闭环。
- [channel脚本](../../examples/channel/export_NRChannel_reference.m)以原生MATLAB独立执行正/负/零/整块TA、连续CFO、实际randn复高斯样本及TA命令换算，24组全向量。Python显式使用保存的单位噪声样本，不要求不同库使用相同PRNG。
- [NROFDM_comparison.json](../../examples/common/NROFDM_comparison.json)由 [比较脚本](../../examples/common/compare_NROFDM_reference.py)实际生成，记录源码/参考哈希、全部组数与误差；清楚区别于MATLAB原始结果。

最大实测波形绝对差约1.048e-9，扰动解调约4.180e-9，符号相位约3.726e-9rad，channel输出约4.966e-16。高载频乘符号时间会产生较大未wrap角度，允许不同浮点运算顺序带来的舍入差。

以下是项目数值比较表，不是3GPP强制一致性阈值。

| 比较项 | 容限 |
|---|---|
| 完整OFDM复波形 | rtol0、atol2e-9 |
| 逐符号未wrap相位 | rtol0、atol2e-8 rad |
| 扰动接收输入的解调网格 | rtol0、atol3e-8 |
| CP长度、TA样点与命令换算 | 精确相等 |
| CFO/含噪输出 | rtol0、atol1e-12 |
| 显式标准噪声缩放 | rtol0、atol1e-15 |

## 单元与时域集成

新增44项单元测试，覆盖精确CP/子帧参考、正负频率bin、DC单音IFFT1/N、提前FFT窗口、相位逆运算、TA不回绕/返回副本、命令Tc换算、CFO分块连续性、复噪声分支方差/seed/显式向量、FFT噪声功率放大Nfft及输入边界。

新增 [SRS时域集成测试](../../tests/integration/test_SRS_waveform_chain.py)：真实SRS网格经逐符号补偿/OFDM，TA提前4点、传播延迟7点、CFO1234Hz、初相0.37rad和AWGN后，已知频偏校正并OFDM解调，既核对解析的延迟频域响应，又检查实际噪声、测得残余3样点、RI2及EVM改善。TA窗口边缘补零，不利用循环回绕伪造完整捕获。

完整本地 **422项通过**：412项单元、9项MATLAB入口、1项时域集成；1070条语句和342个分支全部覆盖，行/分支覆盖率100%。原有SRS/接收/码本等独立参考仍全部通过。

```powershell
.venv\Scripts\python -X utf8 -m pytest --require-matlab --cov=cell --cov=grid --cov=diagnostics --cov=srs --cov=common --cov=channel --cov-branch --cov-report=term-missing --cov-fail-under=100
```

[OFDM示例](../../examples/common/README.md)与 [channel时域SRS示例](../../examples/channel/README.md)均已实际运行并查看图片。时域链路测得RE噪声0.000993659（目标0.001），RMS EVM约190.0%→4.674%，残余3样点/384Tc，RI2/TPMI0。EVM相对于已知MIMO与延迟后的理想网格，不将真实信道本身当作误差。

当前范围：单时隙单numerology、无加窗/重采样、非PRACH、整数TA、有限捕获窗口、已知CFO校正。尚未实现盲CFO/定时估计、TAG调度/TA_offset默认值、多径衰落类和分数时延滤波；逐符号载频补偿不替代各物理信号自身相位/序列算法。原协议资料未修改，本次工作未提交/推送。


2026-10-26 SNR/RSSI/RSRP更新：NRChannel移除显式noise_power输入，唯一加噪入口为snr_db。24组MATLAB信道参考已用整段每支路平均信号功率和SNR重新实际导出，含-5至30 dB、TA裁空后的零信号；保留实际高斯向量而不假设PRNG相同。新增单测验证负/零SNR、拒绝旧noise_power关键字、空输入和极端SNR，时域集成测试采用20 dB配置。SRS参考另24组/32UE重新导出并逐项验证RSSI/RSRP/SNR及每Rx功率；最终误差详见同级链接的比较JSON。
