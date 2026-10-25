# NRSRS 实测验证

日期：2026-10-25。本地实现基线：TS 38.211 V15.2.0 §5.2、§6.4.1.4，TS 38.331 V15.2.1 §6.3.2。实现、同级类说明、示例、实际 MATLAB 结果和测试已完成。远端 CI 状态以 GitHub 实际记录为准。

## 环境与来源

- Python 3.14.0、NumPy 2.5.4；示例 Matplotlib 3.11.2。
- 真实 MATLAB 24.1.0.2537033 (R2024a)，5G Toolbox 24.1。
- 独立生成脚本：[export_NRSRS_reference.m](../../examples/srs/export_NRSRS_reference.m)，调用 MATLAB nrSRS、nrSRSIndices、nrResourceGrid，没有执行或导入 Python 算法。
- 全量实测数据：[NRSRS_reference.json](../../examples/srs/NRSRS_reference.json)，832组，每组保留全部复数值/索引、输入、环境和 UTC 时间。
- 比较脚本：[compare_NRSRS_reference.py](../../examples/srs/compare_NRSRS_reference.py)；输出 [NRSRS_comparison.json](../../examples/srs/NRSRS_comparison.json)，记录原始向量、NRSRS与NRCommon实现 SHA256，明确该文件是 Python 比较报告。

Python 原表常量由项目辅助译文提取，并使用英文 PDF 逐项核对：64行带宽表512个整数、12/24点短序列相位表共1080个整数。原文/译文文件均未修改。没有用 MATLAB 输出生成 Python 算法表。

以下为项目覆盖统计表，**不是协议原表**。

| 参考组 | 数量 | 覆盖内容 |
|---|---:|---|
| 完整带宽表 | 512 | 64行×4层级×comb2/4，n_RRC=67，关闭频率跳频，保留循环移位/comb偏移 |
| 全部短序列组 | 60 | u=0..29×comb2/4；1/2/4端口与符号；非零载波/BWP起点与频域shift |
| numerology/序列跳变 | 36 | 15/30/60/120/240kHz普通CP和60kHz扩展CP×neither/group/sequence×comb2/4，4端口，上半区循环移位及帧内最后时隙 |
| 频率跳频 | 189 | C=1..63×B=1..3；奇/偶 N_b，多层 b_hop，R=1/2/4，frame=0/1023，周期/半持续/非周期，组/序列跳变 |
| 周期边界 | 34 | R15全部17周期，候选与非候选，含 disabled；跨帧计数 |
| 非周期关闭 | 1 | enabled=False 时无序列/RE |
| 合计 | 832 | 不把后续版本定位或8端口扩展纳入 R15 覆盖 |

240kHz 用于基础公式的数学输入覆盖；本测试不声明其在任何特定频段/UE能力下的 SRS 部署适用性。NRCell 目前不进行射频能力/频段组合检查。

## 比较项与误差规则

实测对比累计 **364800 个复数值**，相同数量的 [p,l,k] 坐标。所有索引、u/v、k0/n_b、资源数量均完全一致。最大原始序列/映射点绝对误差 **1.467747412826585e-9**。

| 比较项 | 规则 | 依据 |
|---|---|---|
| 索引、尺寸、u/v、n_b、k0、数量 | 精确相等 | 均为整数资源和确定性PRBS结果 |
| alpha | rtol=0，atol=1e-14 | rad，纯浮点循环移位公式 |
| 每个原始复数点、每个映射值 | rtol=0，atol=2e-9 | Python 对整数 ZC 相位先模2π，MATLAB 直接计算大相位产生舍入差；最大实测误差低于此值 |
| 网格总能量 | rtol=1e-12，atol=1e-10 | 多点平方累加舍入 |
| MATLAB 线性位置加权的复数和 | rtol=0；atol=2e-9*Σ实际RE的1起始线性索引/√P+1e-8 | 从逐点误差上界线性传播；不能对被位置权重放大的和套用原始单点阈值 |

MATLAB nrSRS 返回未施加 1/√P 的原始序列。脚本将其除以 √P 后写入真实 nrResourceGrid（beta=1）；Python generate 与原始序列对齐，map_to_grid 在映射时归一化。原始列顺序、网格轴转换及特殊四端口 comb 位移均独立对比。

MATLAB 载波输入采用 NFrame 与**帧内 NSlot**，与 NRCell.to_matlab_config 一致。不能同时令 NFrame 为当前帧、NSlot 又为绝对累计槽号，否则 MATLAB 将重复累计帧号。PRBS 每帧重置，与用于频率跳频的 SRS 传输计数分开处理。

所有参考配置显式关闭 SRSPositioning、FrequencyScalingFactor>1、StartRBHopping、8端口TDM、CyclicShiftHopping、CombOffsetHopping、HoppingFinerGranularity、HoppingWithRepetition。Python 将 sequence_id 限定为 R15 的10bit，periodicity 限定为 R15 的17种取值，拒绝更新 Toolbox 接受的后续 Release 选项。

## 本地测试与演示

```powershell
.venv\Scripts\python -X utf8 -m pytest --require-matlab --cov=cell --cov=grid --cov=diagnostics --cov=srs --cov=common --cov-branch --cov-report=term-missing --cov-fail-under=100
```

**325项通过**：320项单元测试（原189+SRS109+NRCommon22），5项 MATLAB 独立向量入口（NRCell、NRGrid、NRSRS、Gold比特和公共u/v）。cell/grid/diagnostics/srs/common 共712条可执行语句、212个分支全部覆盖，行/分支覆盖率100%。MATLAB入口循环全部配置；832不是pytest入口数。

SRS 单元测试另外核对手算 C=3/B=1 的跳频排列 0→2→1→3、端口正交性、重复因子、BWP越界整体失败、原子冲突/覆盖、零增益仍占用、错误类型/R15范围、enabled控制及SFN回绕。测试通过不代表完整资源集调度或空口一致性认证。

[示例](../../examples/srs/README.md) 已实际运行，保留同级 JSON/NPZ/CSV、PNG/SVG与忽略的日志；图像已逐张检查。allocation 显示 R=1 的时隙内跳频，hopping 显示 R=4 的时隙间跳频，输入分别记录。频率CSV区分相对 OFDM 居中参考和相对 Point A，后者直接使用 NRCell.subcarrier_offset_hz。

当前覆盖合成序列与频域映射，没有验证 OFDM 时域波形、实际RF功率、信道估计性能、波束/天线预编码、TDD/DCI/MAC许可流程或链路性能；这些功能尚未实现。
