# PUCCH Format 2首版验证

固定TS38.211 V15.2.0 §6.3.2.5、§6.4.1.3.2，TS38.212 V15.2.0 §5.3.3.3、§5.4.3、§6.3.1。首版只实现3～11位小块UCI；12位以上Polar/CRC明确拒绝。不是完整PUCCH调度器或空口性能认证。

## 实际MATLAB参考

环境：MATLAB 24.1.0.2537033 (R2024a)，5G Toolbox 24.1。独立[导出脚本](../../examples/pucch/export_NRPUCCH2_reference.m)实际调用nrUCIEncode、nrPUCCH2、nrPUCCHDMRS、数据/DMRS索引、nrResourceGrid和nrOFDMModulate，输出[真实向量](../../examples/pucch/NRPUCCH2_reference.json)。原始输入、编码位、网格、两接收支路时域波形及环境信息均保存；不是用Python模拟MATLAB结果。

36例覆盖每个K=3..11，1/2符号，1/2/3RB，非零CRB/BWP起点、非零起始符号、RNTI/数据ID/DMRS ID各自配置、跳频开关。普通CP、30kHz、slot3、载波12RB/NStartGrid10，BWP起点11/大小10；两Rx平坦增益0.7+0.4j与-0.3+0.6j。编码位逐位精确比较，网格与全部时域样点比较，并把实际MATLAB波形输入Python接收机验证原始UCI判决。未声称调用Toolbox接收机或比较其性能。

[比较报告](../../examples/pucch/NRPUCCH2_comparison.json)实测：编码位差异0、36例判决差异0、数据/DMRS网格与时域波形最大绝对误差1.5700924586837752e-16（归一化复幅度），容限1e-11。报告保留参考、生成/比较脚本及相关实现SHA256。

```powershell
.venv\Scripts\python -X utf8 examples/pucch/compare_NRPUCCH2_reference.py
.venv\Scripts\python -X utf8 -m pytest --require-matlab -q
```

## 测试与发现

新增59项单元测试及1个MATLAB比较入口；全套655项通过。测试覆盖3..11位编码/软译码、重复/截取、错误输入、资源位置、DMRS模长、普通/扩展CP时域闭环、延迟/CFO/按SNR加噪、零信号DTX和码率不足拒绝。不宣称新增代码100%覆盖率。

参考核验发现：11位UCI截到16位时，原表前16行的第0/10基向量相同，会出现不可区分码字。不能把这种无噪声判决差异用容差掩盖。F2收发接口限制K/E≤0.6，10/11位单符号参考至少分配2RB；调度层仍需按真实配置maxCodeRate选择资源。通用NRSmallBlockCode本身是数学编码工具，不代替调度适用性检查。

## 边界

- 普通CP真实MATLAB已验证；扩展CP、噪声、延迟/CFO补偿目前只做Python链路测试/示例，尚无本模块独立MATLAB该类向量。
- 每符号每RB内假设平坦增益，4个DMRS平均估计；不实现强频率选择性插值、盲同步或多用户联合均衡。
- 输出软分数与白噪声LLR成比例，无独立噪声方差标定。DMRS检测指标不是CRC，默认门限未校准恒定虚警率。
- 未实现Polar/CRC、HARQ/SR/CSI字段拼接、配置maxCodeRate自动调度或DTX性能曲线。
- [示例](../../examples/pucch/NRPUCCH2_demo.py)的7位输入在延迟2采样点、CFO731Hz、SNR15dB后正确恢复，指标约0.999413；绘图只显示，不保存图片。未创建Git提交或推送。

当前更新：F2已接入NRUCICode，解除早期首版3～11位限制；真实MATLAB参考现为56例并覆盖长UCI，当前能力和边界以[新报告](NRPUCCH3_validation.md)为准。
