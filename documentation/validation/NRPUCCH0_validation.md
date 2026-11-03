# PUCCH Format 0收发验证

日期：2026-10-27。基线TS38.211 V15.2.0 §5.2.1、§5.2.2.2表5.2.2.2-2、§6.3.2.2/3、§5.3.1/§5.4；UCI移位依据TS38.213 V15.3.0 §9.2.3表9.2.3-3/-4、§9.2.4正文、§9.2.5.1表9.2.5-1/-2。未使用后续Release的多RB交织等能力。

实现：[资源/序列](../../src/pucch/NRPUCCH0.md)、[发射机](../../src/pucch/NRPUCCH0Transmitter.md)、[接收机](../../src/pucch/NRPUCCH0Receiver.md)、[公共参数](../../src/common/NRCommon.md)、[完整示例](../../examples/pucch/README.md)。候选非相干归一化相关和DTX门限是项目接收算法，不冒充规范强制算法。

## 实际独立MATLAB参考

实际环境：MATLAB 24.1.0.2537033 (R2024a)，5G Toolbox 24.1。运行[export_NRPUCCH0_reference.m](../../examples/pucch/export_NRPUCCH0_reference.m)，不调用Python，保留[原始JSON](../../examples/pucch/NRPUCCH0_reference.json)和[比较报告](../../examples/pucch/NRPUCCH0_comparison.json)。

- 960组公开5G Toolbox序列/RE：20种HARQ/SR输入（1bit或2bit，SR无/负/正，以及SR-only负/正）、1/2符号、neither/enable两种组模式、12个初始循环移位；覆盖跳频、普通/扩展CP、BWP相对CRB偏移、不同slot及hopping_id。
- 40组波形/接收：nrResourceGrid、nrOFDMModulate/nrOFDMDemodulate实际生成/解调，MATLAB原生执行2Rx复增益、3点传播延迟、731Hz CFO、0.23rad初相、12dB整slot SNR噪声与已知同步补偿；保存实际标准复高斯向量，避免要求Python/MATLAB随机数发生器相同。
- 独立接收机用Toolbox候选序列加原生MATLAB相关公式计算所有候选分数，再与Python比较；另保留并核对nrPUCCHDecode的UCI输出。输入来自实际MATLAB接收波形，未用Python接收输出伪造参考。
- SR-only负SR在参考中是零发送波形，按自身SNR产生零噪声；单元测试另以固定随机纯噪声检验DTX，演示还以活动参考校准背景噪声，让DTX不只是全零输入的特例。

## 固定R15的寻址适配

项目原文TS38.211 V15.2.0 §6.3.2.2.2的n_cs寻址含常量14*n_slot。实际R2024a Toolbox默认以CP对应每slot符号数寻址，在extended CP下使用12*n_slot。原文与当前工具实现并非所有输入都完全相同，不能为通过比对静默修改R15公式。

脚本用公开nrPUCCH0显式传normal CP参数，仅使序列阶段采用14寻址；nrPUCCHIndices及实际OFDM仍使用真实extended CP。对已经提取的12*S个RE调用nrPUCCHDecode时，同样仅以normal参数指定序列寻址，并未把extended时域波形当normal CP解调。参考同时保留未适配默认序列toolbox_default_real/imag与sequence_adapter描述。

原始Toolbox默认序列与R15适配序列存在161组差异，最大幅度差2；适配后的全部960组与Python一致。这不是声称未经适配的当前Toolbox完全等同R15，也不是Python输出冒充Toolbox结果。

F0只用12点基序列，§5.2.2定义该长度仅v=0；group_hopping='disable'可能给出v=1，Toolbox亦报低PAPR短序列不支持。资源接口拒绝此模式；公共函数仍可给出其原始u/v参数用于诊断，不用它构造未定义的F0序列。

## 数值结果

下表为项目比较策略与实测误差，不是3GPP空口性能门限。rtol无量纲，atol与被比较量单位一致；复幅度使用归一化单位，候选得分无量纲。

| 项目 | 容限 | 实测最大绝对差 |
|---|---|---|
| 序列复幅度 | rtol0、atol5e-13 | 9.73457324384e-15 |
| OFDM发送波形 | rtol0、atol2e-9 | 4.7875910609e-11 |
| 时域信道输出 | rtol0、atol2e-9 | 4.78759100262e-11 |
| 所有候选相关指标 | rtol0、atol2e-9 | 最大获胜指标差6.66133814775e-16，所有候选逐项断言 |
| 资源功率 | rtol1e-7、atol1e-12 | 40例通过 |
| RE坐标、DTX/HARQ/SR、Toolbox UCI | 精确相等 | 全部零不一致 |

完整参考及实现文件SHA256在比较JSON中；.gitattributes保留参与散列的文件字节，避免Git换行转换破坏核验。

## 单测与集成

本轮全套 **506项通过**（493项单元测试、10个MATLAB入口、3项集成），1257条语句与408个分支全部覆盖，行/分支覆盖率100%。新增3类分别有对应单测，公共函数另有test_NRCommon_pucch.py；原有SRS/OFDM/码本参考继续通过，12点相位表仅移动到common共享，数值不变。

新增集成test_PUCCH0_waveform_chain.py分别覆盖normal30kHz、extended60kHz，2Rx、组跳变、时隙内跳频、TA提前2点/传播延迟5点、CFO731Hz、6dB整slot SNR，再向接收机提供净延迟3点等显式已知补偿参数，HARQ[1,0]+正SR均正确。

```powershell
.venv\Scripts\python -X utf8 -m pytest --require-matlab --cov=cell --cov=grid --cov=diagnostics --cov=srs --cov=common --cov=channel --cov=pucch --cov-branch --cov-report=term-missing --cov-fail-under=100 -q
```

边界：接收机要求12子载波内近似平坦；无独立DMRS、盲同步、多用户联合检测、闭环功控或完整调度。默认DTX门限不保证所有信道下恒定虚警率；未将本测试称为空口接收一致性认证。PUCCH Format1/2/3/4后续实现。


2026-10-27阶段显示验证：新增NRPlotConfig与NRStagePlotter，PUCCH示例默认直接显示27个阶段（5页），不保存PNG/SVG；保留既有数值JSON/NPZ。单测验证禁用不导入Matplotlib、不检查/复制待绘数组、不生成图窗，通配符筛选、数组快照、分页、DTX空序列、共享整链路延迟显示以及禁止savefig；打开/关闭绘图时波形逐元素相同、接收HARQ/SR一致。阶段数据的网格功率和B0相位并排呈现。完整531项通过（518单元、10 MATLAB入口、3集成），1423语句、478分支覆盖率均100%；真实MATLAB参考未修改，OFDM和PUCCH独立比较重新通过并刷新实现哈希。此次仅诊断与展示增强，图像在内存渲染/图窗显示，未另建Git提交或推送。


相关后复平面显示补充（2026-10-27）：新增rx.correlated_constellation，默认活动案例现为28阶段，仍5页；按Rx标记与S0/S1标签显示最佳候选的12点能量归一化复相关输出。返回correlation_symbols[Rx,S]与candidate_correlation_symbols[H,Rx,S]，保留未知信道复增益，不伪造QPSK固定星座；DTX只画最佳噪声假设。独立MATLAB实际重新导出所有候选的复相关向量，40组逐项比较通过，最大绝对误差1.30252911188e-09。全套533项通过（520单元、10 MATLAB入口、3集成），1440语句、486分支覆盖率100%。图像只在内存/图窗显示，未新建PNG/SVG文件；数值NPZ保留复相关数据，比较报告SHA256已同步刷新。

多用户扩展：三UE共用时频资源，通过互斥的完整循环移位候选集合区分；实际MATLAB12案例、36UE结果全部一致。全套553项通过，1463语句/498分支覆盖率100%。详见[多用户验证报告](NRPUCCH0_multiuser_validation.md)。
