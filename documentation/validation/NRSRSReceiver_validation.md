# SRS接收端与上行RI/TPMI验证

日期：2026-10-26。SRS与PUSCH码本固定TS38.211 V15.2.0；参数范围参考TS38.331 V15.2.1。算法、字段及单位见 [接收类](../../src/srs/NRSRSReceiver.md)、[码本类](../../src/common/NRUplinkCodebook.md)。接收机联合FIR LS、噪声/时延估计和互信息搜索是项目算法，未宣称为规范强制接收算法。

## 真实独立参考

MATLAB24.1.0.2537033(R2024a)、5G Toolbox24.1。两个脚本均已实际运行，不调用Python：

- [export_NRUplinkCodebook_reference.m](../../examples/common/export_NRUplinkCodebook_reference.m)调用nrPUSCHCodebook(...,false)，返回规范转置后核对全部72个1/2/4端口码本，保留原表归一化。只用R15表1/3/4/5/6/7，无8端口功能。
- [export_NRSRSReceiver_reference.m](../../examples/srs/export_NRSRSReceiver_reference.m)用真实nrSRS、nrSRSIndices、nrResourceGrid生成参考；MATLAB原生矩阵运算独立建立联合FIR模型，执行A\Y、SVD/pinv、静默RE或残差自由度噪声、最强/首径/均值、逐候选RI/TPMI评分。它验证本项目定义的接收算法，没有将MATLAB代码包装成不存在的Toolbox SRS解调API。
- [NRSRSReceiver_reference.json](../../examples/srs/NRSRSReceiver_reference.json)保留全部接收复数样点、资源/幅度配置、参考噪声、完整预期CIR/频率信道/决策和环境。24组、32个活跃用户结果；包括1/2/4端口、comb2/4、普通/扩展CP、无噪声/AWGN/PRB有色噪声、重叠循环移位/不同序列ID、单径与双径、静默RE与LS残差模式。
- [NRSRSReceiver_comparison.json](../../examples/srs/NRSRSReceiver_comparison.json)由独立Python比较入口实际生成，记录误差、逐用户RI/TPMI/时延与源码/原始数据哈希；明确区别于MATLAB原始输出。

## 结果与容限

全部72个矩阵通过（逐元素atol=1e-15、rtol=0）。接收参考中RI、TPMI、最强径和首径样点、PRB计数完全一致。最大实测CIR绝对差约4.00e-11、频率信道差约8.14e-12、PRB噪声差约4.19e-13。确切结果与SHA256以比较JSON为准。

以下是项目数值比较阈值表，不是协议一致性容差表。

| 项目 | 容限 | 说明 |
|---|---|---|
| 码本矩阵 | rtol0、atol1e-15 | 原表整数/复整数系数和平方根归一化 |
| RI/TPMI、首径/最强径、测量RE数 | 精确相等 | 确定性决策，平分固定低rank/低TPMI |
| CIR/频率信道 | rtol1e-6、atol2e-7 | 容纳参考序列浮点差经伪逆及不同LAPACK实现传播；同时严格检查设计条件数和实际误差 |
| 宽/窄带噪声 | rtol1e-7、atol1e-10 | 复杂能量累加及残差投影，未测PRB按NaN比较 |
| 条件数 | rtol1e-7 | 不同SVD实现的舍入差 |
| 信号功率、平均时延、互信息评分 | rtol1e-6、atol2e-6 | 累加、截负及对数计算，RI/TPMI仍须精确相等 |

Python单元另核对已知CIR和真实注入噪声，包含相同签名拒绝、错误beta/维度/噪声mask、零信号与inactive、BWP外噪声拒绝、首径早于最强径、2.4样点手算RMS扩展、标准矩阵坐标、功率归一化及候选约束。

完整本地回归 **372项通过**（365项单元测试、7项MATLAB入口），行/分支覆盖率100%。旧NRCell/NRGrid/Gold/SRS发送向量仍全部通过。完整命令：

```powershell
.venv\Scripts\python -X utf8 -m pytest --require-matlab --cov=cell --cov=grid --cov=diagnostics --cov=srs --cov=common --cov=channel --cov-branch --cov-report=term-missing --cov-fail-under=100
```

已运行三用户接收示例并逐图检查，保留同级JSON、NPZ、PNG/SVG及忽略的日志。数据种子20261026，RI/TPMI为2/0、1/5、1/0；最强径3/6/1样点。频域Rx输入已完成OFDM和粗同步；延迟是整数样点窗口内残余时延，不是完整TA/测距。首径检测门限、有限模型及白噪声去偏会影响弱径/RMS；有色噪声时不宣称去偏完全无偏。码本选择未加入完整空间干扰协方差或MU-PUSCH调度。

本次修改保留本地待用户检查，未创建Git提交或推送；远端CI状态以实际GitHub记录为准。

2026-10-26时域补充：最新全项目419项测试通过（含实际OFDM/channel参考与SRS时域集成），行/分支覆盖率100%；上文保留对应阶段基线，见[OFDM/channel验证](NROFDM_validation.md)。


2026-10-26补充：信道加噪统一为snr_db，取消直接指定噪声功率。每UE增加归一化RSSI、SRS-RSRP及dB/每Rx功率，SNR以分离后的RSRP和实测宽带噪声计算。RSSI为每SRS符号首末子载波闭区间的带宽总功率（跨符号/Rx平均），RSRP为实际SRS RE平均功率；此为项目工程定义，不冒称R15标准UL测量。实际MATLAB R2024a/5G Toolbox24.1重新导出信道24例和SRS接收24例/32UE；全套422项通过（412单元、9 MATLAB入口、1集成），1070语句/342分支均100%覆盖。示例和类文档同步更新，尚未创建提交。

本次实际MATLAB比对最大绝对误差：SNR 5.25e-12 dB，RSSI 5.69e-14（归一化功率），RSRP 1.97e-13（归一化功率）；每Rx功率也逐项通过。比较报告保留输入参考与实现SHA256，已核验一致。
