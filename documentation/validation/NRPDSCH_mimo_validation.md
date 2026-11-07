# PDSCH多层及DMRS扩展验证

固定TS38.211 V15.2.0 §7.3.1.3及表7.3.1.3-1（1～4层单码字），§7.4.1.1及原表7.4.1.1.2-1/-2（Type1/2端口/CDM/OCC）、-3/-4（单/双符号位置）、-5（支持端口）。编码仍为固定TS38.212 V15.2.0 §7.2的单码块DL-SCH。当前报告取代首版“仅单层/单符号DMRS”的能力限制，旧报告保留历史测试基线。

## 实际MATLAB独立验证

环境MATLAB 24.1.0.2537033 (R2024a)、5G Toolbox24.1。实际运行[多层导出](../../examples/pdsch/export_NRPDSCH_mimo_reference.m)，调用nrDLSCHInfo、CRC/LDPC/速率匹配、nrPDSCH、nrPDSCHDMRS、资源索引和nrOFDMModulate。Tx每层产生真实OFDM波形，再乘非对角满列秩H混合到4根Rx；Python接收端只拿实际Rx波形、资源和同步配置，未把真实H传入估计器。

64例覆盖1～4层、Type1/2、单/双符号DMRS、附加位置（单符号0～3、双符号0/1）、非默认端口选择、QPSK/16/64/256QAM及长度8/10/12/14的Type-A分配。双符号包含同组、同频OCC但不同时OCC的端口，例如Type1的0/4和Type2的1/7；Type2端口还覆盖组2。配置为普通CP30kHz/slot3，载波6RB/NStartGrid10、BWP起点11/大小4、局部PRB1/带宽2，64位TB/目标R0.5/RV0，显式Nref=N。未声称覆盖全部端口排列与全部参数笛卡尔积。

[实际参考](../../examples/pdsch/NRPDSCH_mimo_reference.json)保存完整输入、端口列表、编码位、每层网格、真实复信道及混合Rx波形。[比较报告](../../examples/pdsch/NRPDSCH_mimo_comparison.json)核对编码、网格、波形、估计信道及TB/CRC；所有案例通过。最大网格/信道/时域误差见报告原始字段，均低于1e-10归一化复幅度；编码位/判决精确相等。参考及相关实现SHA256保留，未用Python产生MATLAB向量。

原有32例单层MATLAB参考重新通过，验证接口和CRC结果兼容；公共DL-SCH5例保持通过。信道估计使用已知Gold与端口频域/时域OCC组成联合LS模型，不以分别除参考序列的错误方法代替CDM分离。数据层映射和逆映射严格按原表轮流分配/还原码字符号。

## 自动测试与示例

全套936项通过，综合覆盖率97.14%，保留97%门限；原有cell/grid/channel/diagnostics/srs/基础common及F0的独立100%门限通过。新增测试覆盖DMRS端口签名正交/满秩、附加位置、非法端口/CDM配置、2～4层和Type1/2单/双符号的普通/扩展CP带噪时域链路、零信号、秩亏信道及Rx少于层数拒绝。

[4层示例](../../examples/pdsch/NRPDSCH_mimo_demo.py)：Type2双符号、附加位置1、端口(1,7,4,10)、4Tx/4Rx，16QAM/256位TB/Nref1440。每层真实时域波形经4×4非对角信道叠加，再加2采样点净延迟、731Hz频偏/0.23rad初相和25dB SNR噪声；显式补偿后信道估计/ZF/LDPC正确恢复TB及CRC。图例使用Layer0～Layer3，不能误读为Rx0～Rx3。所有图像仅显示，不保存。

```powershell
.venv\Scripts\python -X utf8 examples/pdsch/NRPDSCH_mimo_demo.py
.venv\Scripts\python -X utf8 examples/pdsch/compare_NRPDSCH_mimo_reference.py
```

## 边界

MATLAB波形参考为普通CP、无噪、已同步的平坦恒定有效信道；扩展CP/噪声/CFO/时延仅Python链路测试。联合LS按RB在整个分配期间估计一个常量矩阵，额外DMRS用于联合观测，不是时变信道插值。ZF要求Rx≥层数，任一RB信道秩亏/条件数过大时equalizer_ok=False、bits=None、crc_ok=False；detected可以独立为True。

未实现5～8层/双码字、多码块、动态预编码/码本、Type-B、MMSE/噪声白化、频选/时间插值、PTRS/预留RE速率匹配或HARQ软合并。层端口域波形不自动匹配物理Tx天线数，示例使用单位预编码，外部H为有效层到Rx信道。未创建Git提交或推送。
