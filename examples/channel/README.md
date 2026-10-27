# channel：TA、噪声和频偏

接口及每个参数/公式见 [NRChannel.md](../../src/channel/NRChannel.md)。本目录与src/channel对应，所有中间文件、参考数据和图像均保存在此处。

**TA直接使用采样点配置**，例如`ta_samples=4`；正数提前，负数延迟。示例JSON显式保存`ta_unit="samples"`。`ta_command`仅记录等效协议命令字段，不是TA时移接口的单位。

```powershell
.venv\Scripts\python -X utf8 examples/channel/NRChannel_demo.py
.venv\Scripts\python -X utf8 -m pytest tests/unit/test_NRChannel.py tests/matlab/test_NRChannel_matlab.py tests/integration/test_SRS_waveform_chain.py --require-matlab
```

以下为项目产物表，不是协议原表。

| 文件 | 用途/结构 |
|---|---|
| [NRChannel_demo.py](NRChannel_demo.py) | main(log)运行单用户2端口/2Rx SRS时域链路，TA→传播延迟→CFO/AWGN→已知CFO校正→OFDM→SRS接收，输出完整输入配置与测量 |
| [NRChannel_summary.json](NRChannel_summary.json) | 小区/SRS/载频/TA命令、样点、传播延迟、CFO、相位、seed、CP比例、时域/RE噪声功率、校正前后EVM、RI/TPMI/估计时延 |
| [NRChannel_data.npz](NRChannel_data.npz) | tx_grid/raw_grid/recovered_grid/ideal_grid:[2,14,288]；tx/advanced/delayed/offset/received/noise/corrected波形均[2,7680]；delay_power:[8] |
| [NRChannel_overview.png](NRChannel_overview.png) / [SVG](NRChannel_overview.svg) | 实际接收SRS波形、每符号补偿角、频偏校正前后EVM和延迟谱 |
| [export_NRChannel_reference.m](export_NRChannel_reference.m) | 原生MATLAB独立零填充移位、指数CFO、实际randn复噪声及TA命令换算；outputFile可选默认同级参考 |
| [NRChannel_reference.json](NRChannel_reference.json) | 24组全部输入/输出复数样点、单位噪声向量、参数、MATLAB/Toolbox/UTC/基线；输入seed登记MATLAB原始向量来源，Python比较显式使用同一噪声样本 |

示例参数：30kHz，24RB，Nfft512，f0=3500000123Hz。相对TA command32→提前4样点，传播延迟7样点，真实/测得残余延迟3样点（384Tc）。CFO=1234Hz、初相0.37rad，接收端使用已知负值校正。目标RE噪声0.001，对应每时域样点噪声1.953125e-6；实际测得RE噪声约0.000994。RMS EVM由约190.0%降至4.674%，RI2/TPMI0。EVM以已知空间矩阵和残余时延后的理想网格作参考，不把真实信道失真本身当作解调误差。

TA和传播延迟采用有限窗口补零，不绕回；CP比例0.5使末符号FFT窗口留出余量，示例延迟满足CP约束。这里没有盲CFO估计、TAG状态机或MAC命令生效调度；支持的整数TA窗口和符号约定见类文档。

```powershell
& 'E:\Program Files\MATLAB\R2024a\bin\matlab.exe' -batch "addpath('examples/channel'); export_NRChannel_reference;"
.venv\Scripts\python -X utf8 examples/common/compare_NROFDM_reference.py
```

比较报告统一保存在 [NROFDM_comparison.json](../common/NROFDM_comparison.json)，同时核对OFDM/相位和24组channel输入。参考波形向量按Python[分支,样点]C-order恢复，对应MATLAB[样点,分支]按列展平。原生MATLAB模型结果没有冒充5G Toolbox不存在的channel API。


加噪仅通过`NRChannel.add_awgn(waveform, snr_db=20, seed=42)`：按每支路整段波形（含静默样点）平均功率计算预期噪声方差，移除直接指定噪声功率的接口。示例JSON记录目标snr_db、派生每Rx时域噪声、接收机每UE SNR/RSSI/RSRP；功率均为归一化值，dB不是dBm。细节见[NRChannel](../../src/channel/NRChannel.md)与[NRSRSReceiver](../../src/srs/NRSRSReceiver.md)。


变量单位与数组维度请对照[公式变量阅读指南](../../documentation/formula_reference.md#implementation)及所链接类文档的逐式变量表。图/JSON中的[P,L,K]为发送端口/slot符号/载波子载波，[Rx,T]为接收支路/时域样点；T依实际CP计算，不把平均slot时长代入取整。
