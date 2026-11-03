# NRCommon 序列示例

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
