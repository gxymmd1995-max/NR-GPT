# PUCCH F0多用户循环移位复用验证

本报告记录实际运行结果。发送基线为TS38.211 V15.2.0 §6.3.2.2/3，候选映射为TS38.213 V15.3.0 §9.2.3、§9.2.5.1。多用户相关、门限及分配检查为项目算法，不是规范规定的接收机。

## 独立参考与范围

实际环境：MATLAB 24.1.0.2537033（R2024a），5G Toolbox 24.1。运行[导出脚本](../../examples/pucch/export_NRPUCCH0_multiuser_reference.m)生成[参考向量](../../examples/pucch/NRPUCCH0_multiuser_reference.json)，再运行[比较脚本](../../examples/pucch/compare_NRPUCCH0_multiuser_reference.py)。[比较结果](../../examples/pucch/NRPUCCH0_multiuser_comparison.json)保留实际环境、误差及参考/实现SHA256。

MATLAB使用真实nrPUCCH0、nrPUCCHIndices、nrResourceGrid及OFDM收发，独立进行逐UE复增益、TA、路径延迟、CFO、时域叠加和SNR加噪。接收候选相关由原生MATLAB独立计算；未声称存在或调用Toolbox多用户联合译码器。既有单用户40例仍另有nrPUCCHDecode比对。

保持固定R15的14*slot伪随机寻址：序列生成使用既有normal参数适配，物理OFDM仍使用案例真实CP。扩展CP每slot为12符号，不能因此改变固定R15序列寻址。详见[单用户报告](NRPUCCH0_validation.md)。

12例覆盖6种活动组合111、110、101、011、100、010，各含普通CP/30kHz与扩展CP/60kHz。变化包括初始移位、ACK比特、SNR -5/0/5dB；3UE共享两符号跳频资源，2Rx，逐UE平坦复增益，公共已知净延迟3采样点和CFO731Hz。波形、输入、噪声标准向量、全部候选复相关/指标与检测结果保存在参考文件中。

## 比较结果

| 比较对象 | 最大绝对误差 | 绝对容限 | 单位/维度 |
|---|---|---|---|
| 三UE混合无噪时域波形 | 2.2084448919134744e-10 | 2e-9 | 归一化复幅度，[Rx,T] |
| 加噪接收时域波形 | 2.2084449829334023e-10 | 2e-9 | 归一化复幅度，[Rx,T] |
| 各候选能量归一化复相关 | 3.781867581393566e-9 | 1e-8 | 归一化复幅度，[H,Rx,S] |
| 归一化相关功率得分 | 5.551115123125783e-16 | 2e-9 | 无量纲，[H] |
| 活动/DTX及HARQ判决 | 0项不一致 | 精确相等 | 12例，共36UE结果 |

上表是实测工程误差表，不是协议原表。H为每UE候选数（本例2），Rx=2，S=2；T为当前slot样点数。3.5GHz附近载频下OFDM相位计算的浮点差约数纳弧度，相关输出幅度约1时形成数e-9复幅度差，因此相关值容限为1e-8；功率得分和判决另行严检，未用该容限掩盖判决差异。

## 自动测试与边界

完整测试553项通过：533单元、11 MATLAB参考入口、9集成；1463语句、498分支覆盖率均100%。集成测试覆盖普通/扩展CP、三/双/单活动UE，验证时域线性叠加、每UE比特/DTX，以及去除独立噪声投影后相关输出等于预期用户增益。单测同时检查完整候选集合碰撞、2bit分配及输入/资源不一致。

```powershell
.venv\Scripts\python -X utf8 -m pytest --require-matlab --cov=cell --cov=grid --cov=diagnostics --cov=srs --cov=common --cov=channel --cov=pucch --cov-branch --cov-report=term-missing --cov-fail-under=100 -q
```

默认演示以初始移位0/2/4区分3UE，候选集合为{0,6}/{2,8}/{4,10}，先检查所有候选互斥。混合功率归一化使单UE指标下降，示例使用工程门限0.15，不提供恒定虚警保证。未验证盲同步、独立残余CFO/时延、强频率选择性、任意近远功率差或联合多用户均衡。演示图直接显示，不保存图像；数值JSON/NPZ按项目约定保留。
