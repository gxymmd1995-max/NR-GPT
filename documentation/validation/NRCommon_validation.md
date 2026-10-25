# NRCommon公共序列验证

日期：2026-10-25。固定基线为TS 38.211 V15.2.0 §5.2.1、§6.4.1.4.2，SRS字段范围参考TS 38.331 V15.2.1 §6.3.2。

Gold生成器和SRS u/v已移至 [NRCommon.py](../../src/common/NRCommon.py)，NRSRS调用公共类；其端口alpha、基序列、频率跳频与RE映射仍在SRS模块。公共接口及所有参数示例见 [NRCommon.md](../../src/common/NRCommon.md)。

独立参考来自实际MATLAB R2024a 24.1.0.2537033、5G Toolbox24.1：

- [export_NRCommon_reference.m](../../examples/common/export_NRCommon_reference.m)调用真实nrPRBS，保留20组种子/长度/offset与全部比特，输出 [NRCommon_reference.json](../../examples/common/NRCommon_reference.json)。最大种子用uint32写出JSON整数，避免科学计数法被Python读取为float；没有放宽公共接口的严格整数校验。
- Gold逐位精确相等，包括种子0和2**31-1、offset=1600、零长度片段。
- 公共SRS u/v直接与已有832组真实SRS参考中的活跃配置比较，结果精确相等，覆盖neither/groupHopping/sequenceHopping、普通/扩展CP与序列长度阈值。
- 原有SRS全向量、全部索引、alpha/k0/n_b、映射网格和能量比较继续通过。没有重新用Python输出替换MATLAB参考。

新增22项公共类单元测试和2项MATLAB入口；全项目325项通过（320项单元、5项MATLAB入口），712条语句和212个分支全部覆盖，行/分支覆盖率100%。

```powershell
.venv\Scripts\python -X utf8 -m pytest --require-matlab --cov=cell --cov=grid --cov=diagnostics --cov=srs --cov=common --cov-branch --cov-report=term-missing --cov-fail-under=100
```

[示例](../../examples/common/README.md)已运行，保存同级Gold/u/v JSON、PNG/SVG和忽略的调用日志。u图与v图分别来自两种互斥配置。SRS比较报告同步重算并保存NRSRS/NRCommon两个源码哈希。该公共类目前覆盖这两个接口，其他公共调制、编码和OFDM功能待实现。远端提交和 CI 状态以 GitHub 实际记录为准。
