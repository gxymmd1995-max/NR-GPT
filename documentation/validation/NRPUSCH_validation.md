# PUSCH首版验证

固定TS38.211 V15.2.0 §5.1、§6.3.1及§6.4.1.1，TS38.212 V15.2.0 §6.2及§5.2.2/5.3.2/5.4.2。首版单层、单码字、CP-OFDM、连续RB、Type-A/Type-1单符号DMRS（AdditionalPosition0、端口0），完整单码块TB CRC/LDPC/RV速率匹配。没有将不支持的多层/多码块/DFT预编码/PTRS/UCI功能伪装成可配置能力。

## 实际MATLAB独立参考

环境MATLAB 24.1.0.2537033 (R2024a)、5G Toolbox24.1。[PUSCH导出脚本](../../examples/pusch/export_NRPUSCH_reference.m)实际调用nrDLSCHInfo（与UL-SCH相同的CRC/BG/Z参数规则）、nrCRCEncode、nrCodeBlockSegmentLDPC、nrLDPCEncode、nrRateMatchLDPC、nrPUSCH、nrPUSCHDMRS和nrOFDMModulate。保留实际版本、原始TB、配置、编码位、网格及完整接收波形；并非Python伪参考。接收端直接输入实际MATLAB波形，不旁路发送网格。

32例覆盖QPSK/16QAM/64QAM/256QAM、RV0～3，BG2/256位/目标R0.5及BG1/512位/目标R0.8，Type-A位置2/3、CDM无数据组1/2、n_SCID0/1。载波12RB/NStartGrid10，BWP起点11/大小10，连续8RB从局部1开始，符号0起始/长度12，普通CP30kHz/slot3，数据ID731/DMRS ID271，两Rx增益0.7+0.4j、-0.3+0.6j。[比较报告](../../examples/pusch/NRPUSCH_comparison.json)中编码位差异0、解码比特差异0、TB CRC及LDPC收敛全部成功；最大网格误差3.1401849173675503e-16、最大时域误差4.291468873614597e-17（归一化复幅度），绝对容限1e-10。报告保留输入/实现SHA256。

另有5组[实际UL-SCH参考](../../examples/common/NRULSCHCode_comparison.json)，覆盖A16/160/256/512/4000、CRC16/CRC24A、BG1/BG2、多种Qm及RV。码字逐位及对实际码字的无噪译码均通过。4000位CRC24A目前是公共编码参考，不是完整PUSCH时域实测。

TBS/目标码率由调用方显式给定，参考为核验算法而选择充分观测长度，不声称这些组合都来自某个标准MCS/TBS调度过程。某些RV单独、部分观测时没有足够系统位，即使无噪也可能无法由最小和迭代恢复；增加迭代次数不保证成功，通常需要足够观测或HARQ合并。测试明确保留一个此类不收敛案例，要求crc_ok=False，而非把全零候选的代数CRC巧合当成功。未以放宽比特检查、跳过失败或伪造译码替代验证。

## Python测试与边界

新增41项单元测试及2个MATLAB入口；全套862项通过，覆盖率检查包含pusch后综合97.13%，达到既有97%门限。测试覆盖QAM平均单位能量/标记点数、资源坐标/保留RE、错误配置、UL-SCH四RV、填充与反速率匹配、非收敛失败、普通/扩展CP四种调制的时域延迟/CFO/SNR噪声链路、零输入无检测。新增代码未声称100%覆盖率。

实际MATLAB参考为普通CP、无噪、已同步。扩展CP、非零资源起始符号、噪声/CFO/延迟补偿目前只有Python测试/示例，未声称已有本模块MATLAB该类向量。接收假设每RB内及整个分配期间近似平坦恒定信道，未实现频选/时间插值或盲同步。软值为等白噪声假设下的比例可靠性，未标定噪声方差；检测指标未校准恒定虚警率。

尚未实现：多码块UL-SCH分段/CRC24B、自动MCS/TBS选择、HARQ软缓冲/合并、MIMO层/码本/TPMI、DFT-s-OFDM、Type-B/Type-2或双符号/额外DMRS、跳频、PTRS及UCI复用。超出单码块限制明确拒绝；CRC24A支持不代表已实现多码块。

[示例](../../examples/pusch/NRPUSCH_demo.py)使用256位TB/16QAM，实际时域信号经过两Rx增益、延迟2采样点、CFO731Hz、SNR25dB，接收正确恢复比特、LDPC收敛且CRC通过。图像只显示，不保存。未创建提交或推送。
