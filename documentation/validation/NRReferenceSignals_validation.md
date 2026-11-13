# CSI-RS 与上下行 PT-RS 验证

## 实现范围

固定TS38.211 V15.2.0。CSI-RS支持原表7.4.1.5.3-1 Row1/2的单端口NZP/ZP、密度3/1/0.5、CRB及slot符号定位、独立OFDM波形和平坦LS/观测参考功率。上行PT-RS为§6.4.1.2的非变换预编码分支；下行为§7.4.1.2。二者支持单层共享信道、DMRS Type1/2对应原表的端口/RE偏移、时间密度1/2/4、频率密度2/4和给定平坦信道后的CPE估计、参考符号反旋及可选的资源内逐符号插值补偿。

这是首版子集，**不代表已完整补齐全部R15参考信号配置**：CSI-RS Row3～18多端口CDM、CSI报告码本、上行DFT-s-OFDM PT-RS、多层/双PT-RS端口尚未实现。PUSCH/PDSCH 可配置 PT-RS，集成接收机使用每 RB 的 DM-RS LS 增益。CSI-RS 的自动数据避让仍待扩展。

## 真实MATLAB参考

[导出脚本](../../examples/common/export_NRReferenceSignals_reference.m)在实际MATLAB R2024a / 5G Toolbox24.1中调用nrCSIRS/nrCSIRSIndices、nrPUSCHPTRS/nrPUSCHPTRSIndices、nrPDSCHPTRS/nrPDSCHPTRSIndices。版本原字符串、全部输入与实际输出见[参考JSON](../../examples/common/NRReferenceSignals_reference.json)。没有用Python结果充当MATLAB参考。

原有99例：CSI-RS Row1密度3、Row2密度1和0.5偶RB，共3例；上行48例、下行48例，覆盖3种时间密度×2种频率密度×2种DMRS类型×4列RE偏移。共同输入52RB/30kHz、普通CP、slot0、RNTI1、单层、共享信道4RB/14符号、首DMRS位置2、AdditionalPosition0；CSI-RS为CRB0起24RB、符号4、NID0。另有5个100 MHz / 30 kHz用例（273 RB、载波起始CRB10、slot7），实际输入由导出脚本和参考JSON保留：

| 资源 | 新增用例 | 验证重点 |
|---|---:|---|
| CSI-RS | 3 | 272 RB，Row1密度3、Row2半密度偶/奇RB；符号9、RB内偏移3、NID511，验证绝对CRB寻址 |
| 上下行PT-RS | 各1 | 起始CRB15的260 RB BWP，BWP内PRB2起257 RB，分配符号1～13，DMRS Type2、首DMRS位置3及附加位置1，NID117、NSCID1、RNTI39，时间间隔2、频率间隔4、偏移列11 |

这些是代表性配置，未穷举全部偏移、端口、时隙和CP。

[比较器](../../examples/common/compare_NRReferenceSignals_reference.py)逐元素比较零基[端口,slot符号,载波子载波]坐标及复序列；坐标须完全相等、序列最大绝对误差小于1e-12。108例均通过，最大复序列绝对误差约1.57e−16。误差明细、环境及源文件/脚本/参考SHA256见[比较报告](../../examples/common/NRReferenceSignals_comparison.json)。CSI-RS Gold按绝对CRB寻址，PT-RS从首DMRS序列取同频率点，未因MATLAB结果改变R15规则。

## Python测试与时域示例

原有131项单元用例，覆盖上述参数、零功率/半密度无点、资源越界/非法类型、映射冲突、OFDM往返、平坦信道估计、双符号DMRS时间跳过、非整除RB频域起点、参考零输入拒绝和CPE反旋。本轮增加相位跨±π、无参考符号处的负载恢复、分配外资源保护及无参考时保持网格的用例。

三个可运行例子：[CSI-RS](../../examples/csirs/NRCSIRS_demo.py)、[上行PT-RS](../../examples/ptrs/NRUplinkPTRS_demo.py)、[下行PT-RS](../../examples/ptrs/NRDownlinkPTRS_demo.py)。CSI-RS通过双Rx复增益和30dB AWGN后估计；PT-RS把参考网格施加逐符号CPE，再真实OFDM调制/解调后，在已知H=1条件下估计和插值相位，并恢复不含参考的符号上的一个示意数据RE。三种参考信号均有[100 MHz时域入口](NR100MHz_30kHz_validation.md)，已接入统一回归。图仅显示、不保存。该CPE模型不是时域连续CFO；不得混同两者。

MATLAB本轮验证参考生成与位置；带噪OFDM、CPE估计及补偿仅有Python链路验证，尚未独立MATLAB验证接收测量结果。

另有 4 个真实 MATLAB 业务链发射参考，覆盖上下行与 DM-RS Type 1/2 的组合。每例比较 PT-RS 坐标与复值、数据 RE 顺序、编码位预算和固定输入位的加扰 QPSK。

[业务链时域示例](../../examples/common/NRSharedChannel_PTRS_demo.py)以同一段接收波形验证上下行补偿前 CRC 失败、补偿后 CRC 通过及相位估计。该接收机实验由 Python 验证。全仓 1442 项测试通过，4081 条语句与 1176 个分支均覆盖。
