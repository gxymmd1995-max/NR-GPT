# PDCCH及DCI首版验证

固定TS38.211 V15.2.0 §7.3.2.1～5及原表7.3.2.1-1、§7.4.1.3；定向核对原文PDF第80/81/89页。固定TS38.212 V15.2.0 §7.3.2～4，原文PDF第98页核验CRC24C前缀24个1、末16位RNTI掩码、n_max9/I_IL1/n_PC0；子块交织和速率匹配依据§5.4.1。未引入后续版本能力。

## 实际MATLAB比较

MATLAB 24.1.0.2537033 (R2024a)、5G Toolbox24.1实际调用nrDCIEncode、nrPDCCHResources、nrPDCCH及nrOFDMModulate，关闭windowing。15例覆盖聚合等级1/2/4/8/16、CORESET持续1/2/3符号、非交织/REG交织、32/12/140位DCI及打孔/缩短/重复。普通CP30kHz、96RB/CRB起点12、slot3、CORESET起始符号1、RNTI4321/ID271；输入及各变体均保存在[导出脚本](../../examples/pdcch/export_NRPDCCH_reference.m)和[实际向量](../../examples/pdcch/NRPDCCH_reference.json)。未把Python生成结果当作MATLAB向量。

[比较结果](../../examples/pdcch/NRPDCCH_comparison.json)：编码位精确一致，所有DCI/CRC通过；最大网格误差1.5700924586837752e-16、波形误差2.1942709178604383e-17，均小于1e-10归一化复幅度容差。接收端对实际MATLAB波形独立估计DMRS信道后解码，未提供真实信道。报告保存输入/实现SHA256。

全仓1141项通过，3559条语句、1052个分支全部覆盖，覆盖率100.00%；CI新增pdcch模块，门限仍100%。新增测试涵盖REG束映射/正交数据参考位置、非法配置、Polar所有速率匹配分支、错误RNTI、损坏可靠度表、普通/扩展CP带噪CFO/采样时延、零输入及共享绘图器。

[时域演示](../../examples/pdcch/NRPDCCH_demo.py)在25dB SNR、731Hz频偏及2采样点延迟下正确恢复32位DCI及CRC。所有图仅显示不保存。实际MATLAB向量为普通CP、无信道扰动；扩展CP/带噪/多Rx及同步补偿为Python链路测试，不能宣称为MATLAB扰动场景验证。

## 边界

只处理显式CORESET和已选候选、已打包/对齐的12～140位DCI；六CRB对齐BWP、单逻辑端口2000、候选内REG的DMRS（sameAsREG-bundle）。不实现CORESET0/搜索空间候选哈希及监测时机调度、盲搜RNTI/长度、DCI字段语义、allContiguousRBs全CORESET参考、非对齐BWP或动态波束。数据加扰RNTI与CRC掩码RNTI分别配置；公共/UE搜索空间ID取值由调用方按固定规范提供。接收SC不是SCL，LS/MRC假设每REG平坦，固定检测门限不是CFAR。本轮未提交或推送。
