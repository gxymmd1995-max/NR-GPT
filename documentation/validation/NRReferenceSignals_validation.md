# CSI-RS与上/下行PT-RS首版验证

## 实现范围

固定TS38.211 V15.2.0。CSI-RS支持原表7.4.1.5.3-1 Row1/2的单端口NZP/ZP、密度3/1/0.5、CRB及slot符号定位、独立OFDM波形和平坦LS/观测参考功率。上行PT-RS为§6.4.1.2的非变换预编码分支；下行为§7.4.1.2。二者支持单层共享信道、DMRS Type1/2对应原表的端口/RE偏移、时间密度1/2/4、频率密度2/4和给定平坦信道后的CPE估计/参考符号反旋。

这是首版子集，**不代表已完整补齐全部R15参考信号配置**：CSI-RS Row3～18多端口CDM、CSI报告码本、上行DFT-s-OFDM PT-RS、多层/双PT-RS端口、频选均衡后相位合并、非参考符号插值/解缠绕及共享信道业务集成尚未实现。现有PUSCH/PDSCH类不自动扣除CSI-RS/PT-RS数据RE；仅可在空网格或由外部已正确避让的资源上调用映射，禁止覆盖编码数据点。

## 真实MATLAB参考

[导出脚本](../../examples/common/export_NRReferenceSignals_reference.m)在实际MATLAB R2024a / 5G Toolbox24.1中调用nrCSIRS/nrCSIRSIndices、nrPUSCHPTRS/nrPUSCHPTRSIndices、nrPDSCHPTRS/nrPDSCHPTRSIndices。版本原字符串、全部输入与实际输出见[参考JSON](../../examples/common/NRReferenceSignals_reference.json)。没有用Python结果充当MATLAB参考。

99例：CSI-RS Row1密度3、Row2密度1和0.5偶RB，共3例；上行48例、下行48例，覆盖3种时间密度×2种频率密度×2种DMRS类型×4列RE偏移。共同输入52RB/30kHz、普通CP、slot0、RNTI1、单层、共享信道4RB/14符号、首DMRS位置2、AdditionalPosition0；CSI-RS为CRB0起24RB、符号4、NID0。未声称MATLAB覆盖全部CRB起点、时隙、端口、长短CP和附加DMRS笛卡尔积。

[比较器](../../examples/common/compare_NRReferenceSignals_reference.py)逐元素比较零基[端口,slot符号,载波子载波]坐标及复序列；坐标须完全相等、序列最大绝对误差小于1e-12。99例均通过。误差明细、环境及源文件/脚本/参考SHA256见[比较报告](../../examples/common/NRReferenceSignals_comparison.json)。CSI-RS Gold按绝对CRB寻址，PT-RS从首DMRS序列取同频率点，未因MATLAB结果改变R15规则。

## Python测试与时域示例

新增131项单元用例，覆盖上述参数、零功率/半密度无点、资源越界/非法类型、映射冲突、OFDM往返、平坦信道估计、双符号DMRS时间跳过、非整除RB频域起点、参考零输入拒绝和CPE反旋。新增源码179语句/44分支均100%覆盖。

三个可运行例子：[CSI-RS](../../examples/csirs/NRCSIRS_demo.py)、[上行PT-RS](../../examples/ptrs/NRUplinkPTRS_demo.py)、[下行PT-RS](../../examples/ptrs/NRDownlinkPTRS_demo.py)。CSI-RS通过双Rx复增益和30dB AWGN后估计；PT-RS把参考网格施加逐符号CPE，再真实OFDM调制/解调后恢复已知H=1条件下的相位。图仅显示、不保存。该CPE模型不是时域连续CFO；不得混同两者。

MATLAB本轮验证参考生成与位置；带噪OFDM、CPE估计及补偿仅有Python链路验证，尚未独立MATLAB验证接收测量结果。

全仓含强制MATLAB参考测试：1408项通过，3977条语句、1152个分支，语句/分支覆盖率100.00%。未降低门限、增加排除或删除原测试。本轮未提交或推送。
