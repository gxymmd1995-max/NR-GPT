# NRCommon 序列示例

## 各信道和参考信号的配置对照

[NRChannel_learning_demo.py](NRChannel_learning_demo.py) 汇集 8 组、23 个可运行的对照案例。每组用同一张图并排显示资源网格和发射波形的 I 分量。终端报告 CRC、参考 RE 数、增益误差或相位误差。

```powershell
# 每次打开一个主题，先看 PDCCH 的 CORESET
.venv\Scripts\python.exe -X utf8 examples/common/NRChannel_learning_demo.py pdcch
# 比较下行共享信道的时域长度
.venv\Scripts\python.exe -X utf8 examples/common/NRChannel_learning_demo.py pdsch
# 固定 PDSCH 分配和 TB，对照均衡星座和 CRC
.venv\Scripts\python.exe -X utf8 examples/common/NRChannel_learning_demo.py pdsch-snr
# 批量验证全部例子
.venv\Scripts\python.exe -X utf8 examples/common/NRChannel_learning_demo.py all --no-plot
```

| 命令中的主题 | 改变的设置 | 看什么 | 深入阅读或练习 |
|---|---|---|---|
| `pdcch` | CORESET 占 1、2、3 个符号，固定 AL4 | 同一个候选的时频形状变化，数据 RE 始终为 216，编码长度始终为 432 bit | [PDCCH 资源与 CCE 映射](../../src/pdcch/NRPDCCH.md) |
| `pdsch`、`pusch` | Type-A 分配 4、7、14 个符号，固定 4 RB、QPSK 和 64-bit TB | 数据 RE 数分别为 168、312、624。观察附加 DM-RS 随分配长度出现的位置 | [PDSCH 示例](../pdsch/README.md) · [PUSCH 示例](../pusch/README.md) |
| `ssb` | PCI 17、18，使用同一个已知时频窗口 | 区分 PSS、SSS、PBCH 和 PBCH DM-RS，比较两种 PCI 的 DM-RS 子载波偏移 | [SSB 搜索示例](../ssb/README.md) |
| `srs` | SRS 1、2、4 个符号，固定 comb 2，同频重复 | 每符号占 24 个梳齿 RE。符号数增加时，观察资源向时隙前部延伸 | [SRS 多用户估计示例](../srs/README.md) |
| `csirs` | Row 1 密度 3、Row 2 密度 1 和 0.5，固定 24 RB | 对照 72、24、12 个参考 RE。半密度只在偶数 CRB 上有参考点 | [CSI-RS 测量示例](../csirs/README.md) |
| `ul-ptrs`、`dl-ptrs` | 时间密度参数 1、2、4，固定 8 RB、频率密度参数 2 | 比较参考符号列表，观察遇到 DM-RS 后参考符号位置的变化 | [上下行 PT-RS 补偿示例](../ptrs/README.md) |

表内案例为项目配置，RE 数由实际资源映射得出。协议依据为 TS 38.211 V15.2.0 §7.3.2 和原表 7.3.2.1-1（PDCCH）、§7.3.1 / §6.3.1 和 §7.4.1.1 / §6.4.1.1（共享信道与 DM-RS）、§7.4.3 和原表 7.4.3.1-1（SSB）、§6.4.1.4（SRS）、§7.4.1.5 和原表 7.4.1.5.3-1（CSI-RS）、§6.4.1.2 / §7.4.1.2（PT-RS）。[协议索引](../../documentation/spec_manifest.md)

PDCCH、PDSCH、PUSCH 用带噪时域收发验证数据位和 CRC。SSB 在给定时频窗口内搜索 PCI 并验证广播载荷。SRS 和 CSI-RS 在固定复增益下演示参考信号估计，PT-RS 在已知平坦信道下对照注入的逐符号相位。右图统一画发射波形。新增对照由 Python 回归验证，各模块的 MATLAB 覆盖范围见[功能矩阵](../../documentation/feature_matrix.md)。

PUCCH 和 PRACH 有独立的长度及格式对照入口。[PUCCH 符号数](../pucch/README.md#不同符号数的时域对照) · [PRACH 长短格式及间隔](../prach/README.md#对照-13-种-prach-格式的时域波形)

配置对照图用同一组 OFDM 符号边界标出网格列和时域样点，终端按类别列出 RE 数。`pdsch-snr` 固定 7 个符号、4 RB、QPSK、64-bit TB 与噪声随机种子，只改 `NRChannel` 的时域样点 SNR。25 dB 案例通过 CRC，−20 dB 案例仍检测到信号但 CRC 失败。此结果对应示例的固定配置与种子，SNR 包含全时隙样点的功率口径。

## 共享信道的 PT-RS 补偿

[NRSharedChannel_PTRS_demo.py](NRSharedChannel_PTRS_demo.py) 固定同一段接收波形，对照补偿前后的星座、CRC 及逐符号相位。将命令末尾的 `dl` 换成 `ul` 即可观察 PUSCH。

```powershell
.venv\Scripts\python.exe -X utf8 examples/common/NRSharedChannel_PTRS_demo.py dl
```

## OFDM和逐符号相位

[NROFDM](../../src/common/NROFDM.md)进行单时隙OFDM调制/解调，[NRPhaseRotation](../../src/common/NRPhaseRotation.md)提供R15逐符号载频补偿和提前FFT窗口/定时相位因子。TA/噪声/CFO在 [channel示例](../channel/README.md)。

```powershell
.venv\Scripts\python -X utf8 examples/common/NROFDM_demo.py
.venv\Scripts\python -X utf8 examples/common/compare_NROFDM_reference.py
```

| 产物 | 用途（项目说明表） |
|---|---|
| [NROFDM_demo.py](NROFDM_demo.py) | main(log)生成60kHz slot1双分支网格、波形、CP和相位，记录全部类变量并画图 |
| [NROFDM_summary.json](NROFDM_summary.json) | cell、carrier_frequency_hz、cp_fraction、每符号角度/phasor实虚部/CP、实际slot长度、FFT缩放和恢复误差 |
| [NROFDM_data.npz](NROFDM_data.npz) | grid/recovered_grid:[2,14,288]；waveform:[2,7672]；symbol_phasors:[14] |
| [NROFDM_overview.png](NROFDM_overview.png) / [SVG](NROFDM_overview.svg) | 波形、逐符号相位、CP和星座恢复；60kHz slot1长度249.739583µs |
| [export_NROFDM_reference.m](export_NROFDM_reference.m) | 真实nrOFDMModulate/nrOFDMDemodulate/nrOFDMInfo，显式Nfft和Windowing0；outputFile可选 |
| [NROFDM_reference.json](NROFDM_reference.json) | 28组调制/相位、84组解调全向量，含确定性非OFDM扰动接收输入及CP比例0/0.5/1，MATLAB/Toolbox/UTC/固定基线 |
| [compare_NROFDM_reference.py](compare_NROFDM_reference.py) | compare(log)验证全部OFDM、相位、扰动解调及channel向量，成功才保存报告 |
| [NROFDM_comparison.json](NROFDM_comparison.json) | Python比较报告：最大误差、组数、逐组波形误差、源码/参考SHA256；不是MATLAB原始输出 |

```powershell
& 'E:\Program Files\MATLAB\R2024a\bin\matlab.exe' -batch "addpath('examples/common'); export_NROFDM_reference;"
```

复数grid向量按Python[P,L,K]C-order恢复，波形按[P,T]C-order恢复，对应MATLAB[K,L,P]/[T,P]的列优先展平。显式载频和CP窗口参数避免依赖MATLAB默认FFT、加窗和CP比例；当前仅R15 numerology，不使用480/960kHz扩展。

新增 [NRUplinkCodebook](../../src/common/NRUplinkCodebook.md)提供上行RI/TPMI的72个R15标准矩阵与评分搜索。独立脚本 [export_NRUplinkCodebook_reference.m](export_NRUplinkCodebook_reference.m)生成 [真实矩阵参考](NRUplinkCodebook_reference.json)，使用nrPUSCHCodebook并将其输出非共轭转置；7种端口/层数组合，共72个矩阵，MATLAB R2024a 5G Toolbox环境记录在JSON中。接收演示和选择对比位于 [SRS接收示例](../srs/README.md)。

```powershell
.venv\Scripts\python -X utf8 examples/common/NRCommon_demo.py
.venv\Scripts\python -X utf8 -m pytest tests/unit/test_NRCommon.py tests/matlab/test_NRCommon_matlab.py --require-matlab
```

静态类的完整变量/函数、种子bit顺序和公式出处见 [NRCommon.md](../../src/common/NRCommon.md)。所有产物与脚本同目录。

| 文件 | 用途（项目说明表） |
|---|---|
| [NRCommon_demo.py](NRCommon_demo.py) | main(log)演示Gold 128bit、30kHz一帧内SRS u/v，写JSON和图片；调用链日志和序列内容输出到同级log |
| [NRCommon_sequences.json](NRCommon_sequences.json) | c_init/gold_length/gold_offset/gold_bits；cell/symbol_start/n_symbols/sequence_length；frame_symbol_indices/group_hopping_u/sequence_hopping_v，后两者来自两个互斥的配置 |
| [NRCommon_sequences.png](NRCommon_sequences.png) / [SVG](NRCommon_sequences.svg) | Gold二进制阶梯图和每个SRS符号的u/v散点图，公式出处标在图片中 |
| [export_NRCommon_reference.m](export_NRCommon_reference.m) | outputFile可选，默认同级NRCommon_reference.json；独立使用nrPRBS，不调用Python |
| [NRCommon_reference.json](NRCommon_reference.json) | MATLAB/Toolbox版本、UTC时间、固定基线与20组input/bits；种子0/1/42/1023/2**31-1，长度1/31/128/0，含offset17/1600 |

```powershell
& 'E:\Program Files\MATLAB\R2024a\bin\matlab.exe' -batch "addpath('examples/common'); export_NRCommon_reference;"
```

参考比特必须来自实际MATLAB运行。SRS的u/v继续使用 [NRSRS_reference.json](../srs/NRSRS_reference.json) 中nrSRS返回的SeqGroup/NSeq，避免重构公共层时替换或伪造既有参考。非活跃case的u/v不作为发送参考比较。


变量单位与数组维度请对照[公式变量阅读指南](../../documentation/formula_reference.md#implementation)及所链接类文档的逐式变量表。图/JSON中的[P,L,K]为发送端口/slot符号/载波子载波，[Rx,T]为接收支路/时域样点；T依实际CP计算，不把平均slot时长代入取整。

信道编码：运行python examples/common/compare_NRChannelCodes_reference.py。NRChannelCodes_reference.json由同目录export_NRChannelCodes_reference.m实际生成；Polar/LDPC调用5G Toolbox，经典RM使用独立MATLAB多项式求值。compare(write_report=True)写比较摘要，False不写；不保存图像。

完整UCI参考：export_NRUCICode_reference.m实际调用nrUCIEncode生成NRUCICode_reference.json；运行compare_NRUCICode_reference.py逐位对比并译码，compare(write_report=True)默认写比较报告。覆盖15组小块/Polar/CRC/PC/打孔/缩短/重复/分段；不把LDPC用于PUCCH。

单码块UL-SCH参考：export_NRULSCHCode_reference.m实际生成NRULSCHCode_reference.json；运行compare_NRULSCHCode_reference.py比较CRC16/24A、BG1/BG2及RV速率匹配，compare(write_report=True)写摘要，False不写。5组实际向量通过，完整PUSCH示例在examples/pusch/。

单码块DL-SCH参考：export_NRDLSCHCode_reference.m实际生成NRDLSCHCode_reference.json，compare_NRDLSCHCode_reference.py比较CRC16/24A、BG1/BG2及有限Nref的RV选择，5组实际向量通过；compare(write_report=True)写摘要，False不写。PDSCH完整时域示例见examples/pdsch/。

## 各信道文档配图

[plot_NRChannel_documentation.py](plot_NRChannel_documentation.py)从实际资源类生成11张图：PUCCH F0～F4、PUSCH、PDSCH、PDCCH、SRS、SSB和PRACH。统一52 RB/30 kHz小区，普通CP；PRACH自身间隔15 kHz。各图保存在对应模块examples目录，类文档直接引用。

```powershell
# 默认只显示，不保存
.venv/Scripts/python -X utf8 examples/common/plot_NRChannel_documentation.py
# 明确导出静态文档配图
.venv/Scripts/python -X utf8 examples/common/plot_NRChannel_documentation.py --save
```

依赖项目plots可选依赖。优先使用Microsoft YaHei/SimHei显示中文；其他系统需安装中文字体。图中资源来自indices而非手画；CP时间轴由NRCell推导，PRACH相关来自真实时域叠加与接收算法；没有新增或替代MATLAB参考向量。

参考信号独立比对：MATLAB运行`addpath('examples/common'); export_NRReferenceSignals_reference`；Python运行`examples/common/compare_NRReferenceSignals_reference.py`。99例配置/实际序列/索引保存在NRReferenceSignals_reference.json，环境和误差/SHA256见NRReferenceSignals_comparison.json。CSI-RS与PT-RS示例分别在examples/csirs、examples/ptrs。
