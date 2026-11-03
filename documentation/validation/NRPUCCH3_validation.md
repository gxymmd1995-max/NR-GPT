# PUCCH2公共编码接入与PUCCH3验证

固定TS38.212 V15.2.0 §5.1/5.2.1/5.3.1/5.4.1及§6.3.1，TS38.211 V15.2.0 §6.3.2.5/6、§6.4.1.3.2/3。此报告为当前能力，取代早期F2“仅3～11位”的限制；旧验证报告保留当时的历史结果。

## 实际MATLAB独立对比

环境MATLAB 24.1.0.2537033 (R2024a)，5G Toolbox 24.1。所有参考来自实际运行；UCI调用nrUCIEncode，F2/F3调用nrPUCCH2/3、nrPUCCHDMRS、相应索引和nrOFDMModulate。参考含原始输入、编码位、完整网格/时域波形和实际版本，比较报告记录SHA256；未使用Python输出冒充MATLAB。

| 对象 | 实际案例及结果 | 入口 |
|---|---|---|
| 公共UCI | 15例；小块、CRC6/11、普通/最小行重PC、打孔/缩短/重复、双块分段、A1706；编码位、对实际码字的译码及CRC全部一致 | examples/common/export_NRUCICode_reference.m、compare_NRUCICode_reference.py |
| F2 | 56例，A3～11及12/19/20/32/48；1/2符号、带宽/跳频变化、非零BWP/CRB起点；编码位和UCI判决差异0，网格/时域最大误差1.5700924586837752e-16 | examples/pucch/export_NRPUCCH2_reference.m、compare_NRPUCCH2_reference.py |
| F3 | 22例；长度4～14逐个覆盖、QPSK/π/2-BPSK、1/2/3/6RB、跳频及额外DMRS变化，A7～32；编码位/判决差异0，CRC全部通过；最大网格误差1.3956390167654135e-12、最大时域误差1.466286836819537e-14 | examples/pucch/export_NRPUCCH3_reference.m、compare_NRPUCCH3_reference.py |

上表为项目实测结果，不是规范原表。复数误差单位为归一化幅度；F2绝对容限1e-11，F3为1e-10。F3长序列的循环移位复指数计算存在微小数值差，实际码字、CRC和判决单独精确核对。接收以MATLAB实际时域波形为输入，不旁路读取发送网格。

MATLAB波形参考为普通CP/30kHz、已同步、无噪、两Rx平坦复增益。F3扩展CP、噪声/CFO/整数时延补偿，以及无跳变/序列跳变配置目前未全部覆盖独立MATLAB向量；它们的支持范围和未验证边界不能混同。Python测试另覆盖普通/扩展CP、QPSK/π/2-BPSK、CRC6/11、带噪时域闭环；不将单元测试当作MATLAB实测。

## 接口与限制

PUCCH2/3调用[NRUCICode](../../src/common/NRUCICode.md)：A≤11走现有NRSmallBlockCode，A≥12走公共Polar变换与完整UCI外层处理。LDPC不用于PUCCH，经典RM(r,m)也不替代NR固定小块基矩阵。NRPolarCode原有母码接口保留，新增transform供已配置PC/冻结位调用。

接收采用PC约束SC，不是CRC辅助SCL；低SNR性能未作等价保证。信号检测detected与crc_ok独立，CRC失败仍返回候选位，调用方不能当作传输成功。F2每RB每符号平坦估计，F3每跳整体平坦估计，不含强频选均衡、盲同步、联合多用户接收或调度闭环。

新增示例NRPUCCH2_Polar_demo.py和NRPUCCH3_demo.py：32位UCI，时域信号经两Rx增益、延迟2采样点、CFO731Hz、SNR15dB，显式已知同步补偿后恢复全部比特，CRC通过。默认图只显示、不保存，关闭绘图使用NRPlotConfig(enabled=False)。

```powershell
.venv\Scripts\python -X utf8 examples/pucch/NRPUCCH2_Polar_demo.py
.venv\Scripts\python -X utf8 examples/pucch/NRPUCCH3_demo.py
.venv\Scripts\python -X utf8 -m pytest --require-matlab -q
```

全套779项测试通过；未声称新增代码100%覆盖率。未创建Git提交或推送。
