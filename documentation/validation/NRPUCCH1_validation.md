# PUCCH Format 1验证

固定TS38.211 V15.2.0 §5.1、§6.3.2.2、§6.3.2.4及§6.4.1.3.1。实现[资源](../../src/pucch/NRPUCCH1.md)、[发射](../../src/pucch/NRPUCCH1Transmitter.md)、[接收](../../src/pucch/NRPUCCH1Receiver.md)。

实际环境MATLAB 24.1.0.2537033 (R2024a)，5G Toolbox 24.1。[导出脚本](../../examples/pucch/export_NRPUCCH1_reference.m)调用nrPUCCH1、nrPUCCHDMRS、资源索引和nrOFDMModulate，产生独立网格、DMRS、两Rx复增益时域接收波形。[参考向量](../../examples/pucch/NRPUCCH1_reference.json)不是Python输出。原生MATLAB接收向量输入Python接收机进行比特判决，未声称使用Toolbox接收机。

68组覆盖普通CP、30kHz、slot3、6RB、起始符号0、QPSK，资源长度4～14、跳频开关、各合法OCC索引、变化循环移位，组跳变enable。OCC四阶Walsh特殊顺序及每跳DMRS/数据独立重置均通过真实向量核验。MATLAB和Python载波SCS显式统一；不依赖Toolbox默认值。

[比较报告](../../examples/pucch/NRPUCCH1_comparison.json)：所有网格/时域波形最大绝对误差9.766186892276451e-15（归一化复幅度），容限1e-11；68组比特判决无差异。保留环境、输入及相关文件SHA256。运行`python examples/pucch/compare_NRPUCCH1_reference.py`可复验。

新增41项Python测试覆盖资源几何、单位模、非法配置、Walsh顺序、所有1/2bit输入、普通/扩展CP、经过延迟/CFO/SNR噪声的真实时域闭环、零输入DTX。全套`pytest --require-matlab -q`为595项通过。未对新增类声称100%覆盖率。

边界：BPSK、扩展CP、非零起始符号与噪声/频偏补偿目前仅有Python测试或示例，尚未独立MATLAB核验；本次MATLAB为普通CP/QPSK的无噪声已同步参考。信道估计假设每跳12子载波内平坦且时间近似恒定；没有盲同步、强频选均衡、SR资源选择、跨slot重复、联合多用户接收或恒定虚警保证。示例图只显示不保存。无Git提交或推送。
