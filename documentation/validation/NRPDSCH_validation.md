# PDSCH首版验证（历史基线）

固定TS38.211 V15.2.0 §5.1/5.2.1、§7.3.1/§7.4.1.1，TS38.212 V15.2.0 §7.2及§5.2.2/5.3.2/5.4.2。首版单层单码字CP-OFDM，连续非交织PRB，Type-A/Type-1单符号DMRS（端口1000、AdditionalPosition0）；完整单码块DL-SCH TB CRC/LDPC及有限缓冲RV速率匹配。未将多层、双码字、预留RE或多码块功能伪装成已实现配置。

## 实际MATLAB独立比对

MATLAB 24.1.0.2537033 (R2024a)，5G Toolbox24.1。[实际导出](../../examples/pdsch/export_NRPDSCH_reference.m)调用nrDLSCHInfo、nrCRCEncode、nrCodeBlockSegmentLDPC、nrLDPCEncode、nrRateMatchLDPC（显式Nref）、nrPDSCH、nrPDSCHDMRS及nrOFDMModulate。输入TB、配置、完整编码位/网格/时域接收波形和版本保存在实际参考JSON；接收以MATLAB实际波形为输入，未读取发送网格捷径或伪造MATLAB结果。

32例覆盖QPSK/16QAM/64QAM/256QAM、RV0～3，BG2/256位/目标R0.5与BG1/512位/目标R0.8；Type-A位置2/3、CDM组1/2、n_SCID0/1，Nref=N与Nref=ceil(0.8N)。载波12RB/NStartGrid10、BWP起点11/大小10、局部起始RB1/带宽8RB、符号0起始/长度12、普通CP30kHz/slot3、数据ID731/DMRS ID271，两Rx增益0.7+0.4j、-0.3+0.6j。

[比较报告](../../examples/pdsch/NRPDSCH_comparison.json)：编码位差异0、解码比特差异0，所有TB CRC/LDPC收敛成功；最大网格误差3.1401849173675503e-16，最大时域误差4.5102810375396984e-17，均为归一化复幅度，容限1e-10。SHA256记录参考、导出/比较脚本及相关实现。

另5组[公共DL-SCH实际参考](../../examples/common/NRDLSCHCode_comparison.json)覆盖A16/160/256/512/4000、CRC16/CRC24A、BG1/BG2、调制位交织、不同RV及有限Nref。编码位和对实际码字的无噪译码均通过。4000位CRC24A仅为公共编码独立参考，不声称已有该TB的PDSCH时域实测。

TBS、R、Nref是为算子验证而显式给定，未声称所有组合均来自完整标准MCS/TBS与UE能力选择流程。DL-SCH按R15 §7.2.5的I_LBRM=1执行Ncb=min(N,Nref)；None明确对应Nref=N的非限制性边界，并非自动推导TBS_LBRM。有限缓冲之外为未知零LLR，不是已知零比特。

## Python测试与边界

新增40项单元测试及2个MATLAB入口，全套904项测试通过。测试包括有限缓冲索引界限/RV0～3、Nref类型校验、QAM单位能量/星座标记、资源坐标与保留RE、错误映射/容量/输入、普通/扩展CP四种调制的延迟/CFO/SNR噪声闭环和零信号不译码。实测综合覆盖率97.13%，保持现有97%门限，不声明新增模块100%覆盖。

MATLAB参考为普通CP、无噪且已同步；扩展CP、非零分配起始符号、噪声/CFO/时延补偿目前只做Python测试与示例，未声称独立MATLAB已覆盖这些场景。每RB信道在分配期间假设平坦恒定，未实现频选/时间插值；软可靠性没有噪声方差标定，检测门限未校准恒定虚警率。

尚未实现：多层/双码字、码本与预编码、Type-B/Type-2/双符号/额外DMRS、VRB交织、PTRS、SSB/PBCH/CORESET等预留RE速率匹配、MCS/TBS/Nref自动选择、多码块CRC24B分段、HARQ软合并或PDCCH调度。部分RV或过小Nref单独接收可能不收敛，失败时不报CRC成功。

[示例](../../examples/pdsch/NRPDSCH_demo.py)的256位TB/16QAM/Nref1440，经两Rx增益、延迟2采样点、CFO731Hz及SNR25dB后正确恢复，LDPC收敛且TB CRC通过。阶段图只显示、不保存。未创建Git提交或推送。

当前多层及DMRS能力已扩展，首版限制由[新报告](NRPDSCH_mimo_validation.md)取代；上文保留原904测试/单层参考的历史基线。
