# PUCCH Format 0完整时域收发示例

比较 F0～F4 的占用时长与 DM-RS 位置，见[不同符号数的时域对照](#不同符号数的时域对照)。

## 12种循环移位同图显示

运行[plot_NRPUCCH0_cyclic_shifts.py](plot_NRPUCCH0_cyclic_shifts.py)：

```powershell
.venv\Scripts\python -X utf8 examples/pucch/plot_NRPUCCH0_cyclic_shifts.py
```

单张复平面图显示k=0..11的12个单位圆点，逐点标注索引与角度，间距30度。使用NRCommon实际生成的同根12点序列，除去零移位基础序列，并选频率序号n=1的点。依据TS38.211 V15.2.0 §5.2.2.2、§6.3.2.2/3；下式为本文自编号CS-PLOT-1，不是规范原公式编号：

$$
p_k=\frac{r_k[1]}{r_0[1]}=e^{j\alpha_k},\qquad \alpha_k=\frac{2\pi k}{12}. \tag{CS-PLOT-1}
$$

| 变量 | 含义 | 范围、单位与维度 |
|---|---|---|
| k | 总有效循环移位索引；本图不加入公共Gold跳变 | 整数0..11，标量 |
| n | RB内序列/频率索引；本图取1以观察完整12点圆 | 整数0..11，标量 |
| r_k | 第k种循环移位后的12点序列，用于比较12种移位 | 范围：k=0..11；每点单位模复数；单位：归一化复幅度；维度：complex[12]，12种合并为[12,12] |
| r_0 | 本例零循环移位的12点参考序列，用于去参考 | 范围：每点单位模复数，固定u=0；单位：归一化复幅度；维度：complex[12] |
| alpha_k | 每频率索引的相位步进 | 0..11π/6，rad；全部移位[12] |
| p_k | 去除基础序列后n=1处的相位因子 | 无量纲单位模复数；全部点[12] |
| j | 虚数单位 | 无量纲标量 |

这张图说明循环移位相位，不是接收相关后的信道增益星座，也不代表12个UE可以同时承载任意UCI。固定k后沿n观察相位因子可能重复，例如k=6仅有正负两个点；当前图是固定n=1、遍历k。

`build_data()`无参数，返回shifts[12]、alpha_rad[12]、sequences[12,12]、phase_factors[12,12]和points[12]字典；单位/轴见上表。`main(log=None,plot_config=None)`返回同一字典，默认非阻塞显示；log为可选ExampleLogger，仅打印角度摘要。传入`NRPlotConfig(enabled=False)`禁用绘图且不导入Matplotlib；本独立单图示例只使用enabled字段。脚本入口等待关闭窗口，不保存PNG/SVG或数值产物；ExampleLogger日志仍按项目约定本地生成。

## 三用户循环移位复用

[NRPUCCH0_multiuser_demo.py](NRPUCCH0_multiuser_demo.py)运行两个案例：三个UE同时发送，以及UE2静默、UE0/UE1发送。三个发射机各自产生完整时域波形，经过各自复信道增益后叠加；统一添加AWGN，再把同一份混合波形交给三个独立接收机。接收机不获取实际活动用户集合或实际比特。

```powershell
.venv\Scripts\python -X utf8 examples/pucch/NRPUCCH0_multiuser_demo.py
.venv\Scripts\python -X utf8 examples/pucch/compare_NRPUCCH0_multiuser_reference.py
```

下表为示例配置派生表，依据TS38.211 V15.2.0 §6.3.2.2/3及TS38.213 V15.3.0 §9.2.3、§9.2.5.1；不是规范原表。配置为1bit HARQ、无SR，候选m_cs为0/6。集合尚未加入各UE相同的逐符号n_cs。

| UE | initial_cyclic_shift | 全部合法候选移位 | 本例发送HARQ | 三UE活动时检测得分 |
|---|---|---|---|---|
| UE0 | 0 | 0、6 | 0 | 0.375802 |
| UE1 | 2 | 2、8 | 1 | 0.299562 |
| UE2 | 4 | 4、10 | 0 | 0.292776 |

不能只检查初始移位不同：例如0与6的1bit HARQ候选集合完全相同，会冲突。示例在发送前调用`NRPUCCH0Receiver.validate_cyclic_shift_group`检查所有合法UCI候选。2bit HARQ且无SR时，可用初始移位0、1、2形成集合{0,3,6,9}、{1,4,7,10}、{2,5,8,11}；此规划已单测覆盖。增加SR后候选集合会变化，必须重新校验。

默认小区6RB、30kHz、2Rx、slot3；BWP起点11、大小4RB，三UE均使用BWP局部PRB0→3的相同两符号跳频资源（start_symbol=8），hopping_id=731、组跳变enable。公共TA提前2采样点、传播延迟5点、净延迟3点、CFO731Hz、初相0.23rad均显式补偿；各用户增益在每RB内平坦。用户之间存在不同残余时延/CFO或强频率选择性时不保证分离，当前无联合均衡/SIC。

SNR=-5dB针对混合波形的整slot、逐Rx平均功率，包含静默样点，不是每UE的RE级SNR。归一化检测分母包含其他用户功率，门限显式取0.15；近远效应可能使弱UE漏检。UE2静默案例得分约0.004269，正确判DTX；其余UE仍正确译码。

`run_case(name='all_active', active_users=('UE0','UE1','UE2'), *, initial_shifts=(0,2,4), snr_db=-5, detection_threshold=.15, cyclic_prefix='normal', subcarrier_spacing_khz=30, plot_config=None)`只在内存运行，不写文件。name为案例/图名前缀；active_users是发送侧活动UID集合；initial_shifts为三UE索引0..11；snr_db为有限dB；门限无量纲0..1；CP/SCS遵守NRCell规则（extended仅60kHz）。plot_config为NRPlotConfig或None（关闭）。返回(summary字典, arrays字典, per_user_results字典, NRStagePlotter)。arrays含每UE发射[1,T]、过信道[2,T]、混合/接收/噪声[2,T]、复相关[2,2]，单位为归一化复幅度；T为当前slot样点数。

`main(log,plot_config=None)`运行上述两例，保存[数值摘要](NRPUCCH0_multiuser_summary.json)和`NRPUCCH0_multiuser_data.npz`，返回摘要字典。log为ExampleLogger；默认显示all_active三个UE的候选得分、相关星座、候选Gram矩阵及混合波形，共2页，不保存图像。设置`NRPlotConfig(enabled=False)`关闭全部绘图；stages可选`('all_active.UE0.*',)`等通配符。相关图保留每UE信道复增益，横纵轴为归一化I/Q幅度，不是固定QPSK判决点。

独立参考入口：[MATLAB导出](export_NRPUCCH0_multiuser_reference.m)、[实际参考向量](NRPUCCH0_multiuser_reference.json)、[Python比较](compare_NRPUCCH0_multiuser_reference.py)、[比较摘要](NRPUCCH0_multiuser_comparison.json)、[验证报告](../../documentation/validation/NRPUCCH0_multiuser_validation.md)。覆盖12个案例、36个UE判决；包括普通/扩展CP和不同活动组合。

运行`NRPUCCH0_demo.py`：HARQ-ACK/SR→[NRPUCCH0](../../src/pucch/NRPUCCH0.md)→NRGrid→[发射机](../../src/pucch/NRPUCCH0Transmitter.md)的NROFDM→[NRChannel](../../src/channel/NRChannel.md)→[接收机](../../src/pucch/NRPUCCH0Receiver.md)的OFDM/候选相关/DTX。接收输入为经过信道的时域波形，不旁路使用发送网格。

```powershell
.venv\Scripts\python -X utf8 examples/pucch/NRPUCCH0_demo.py
.venv\Scripts\python -X utf8 examples/pucch/compare_NRPUCCH0_reference.py
```

默认24 RB、30 kHz、2Rx、2个符号、BWP局部PRB1→17跳频；初始循环移位5、hopping_id731、组跳变enable。信道先TA提前2采样点、传播延迟5采样点，净延迟3点，CFO731 Hz、初相0.23 rad，SNR=-5 dB。

SNR以各Rx整slot波形功率为参考，包含静默样点；它不等于活跃RE上的SNR。负SR-only不发信号，因此无法从其自身零功率定义SNR：示例用首个活动参考波形调用同一snr_db接口，取返回的噪声作为DTX背景。没有恢复直接指定噪声功率的入口。接收机显式使用已知CFO/初相/净时延作补偿，未宣称盲同步；频域12点内近似平坦信道。

| 文件 | 用途与格式 |
|---|---|
| [NRPUCCH0_demo.py](NRPUCCH0_demo.py) | main(log)构造4种HARQ/SR输入并运行完整时域闭环，打印类状态和函数路径 |
| [NRPUCCH0_summary.json](NRPUCCH0_summary.json) | 小区/资源/信道/种子、每例发送比特、检测比特、DTX、候选得分与门限；不倾倒整个接收网格 |
| [NRPUCCH0_data.npz](NRPUCCH0_data.npz) | case_0..3的发送波形[1,T]、接收/噪声波形[Rx,T]、发送网格[1,L,K]及接收网格[Rx,L,K] |
| NRPUCCH0_overview.png / .svg | 之前生成的历史静态概览；新交互绘图不再生成或覆盖这些文件 |
| NRPUCCH0_demo.log | 自动生成的完整调用和字段状态日志，Git忽略，不作为参考向量 |
| [export_NRPUCCH0_reference.m](export_NRPUCCH0_reference.m) | 真实MATLAB 5G Toolbox导出960组序列/坐标及40组独立时域接收用例，含R15固定14寻址适配说明 |
| [NRPUCCH0_reference.json](NRPUCCH0_reference.json) | 保存实际MATLAB环境、输入、原始/适配序列、坐标、波形、噪声向量、候选得分及Toolbox译码结果 |
| [compare_NRPUCCH0_reference.py](compare_NRPUCCH0_reference.py) | compare(logger=None,write_report=True)逐项断言，resource_from_input(data)恢复配置；命令入口带ExampleLogger |
| [NRPUCCH0_comparison.json](NRPUCCH0_comparison.json) | Python比较报告及SHA256，含真实参考的误差与逐例判决；不是MATLAB原始结果 |

### 生成独立MATLAB参考

需真实MATLAB R2024a和5G Toolbox24.1；脚本不调用Python。

```powershell
& 'E:\Program Files\MATLAB\R2024a\bin\matlab.exe' -batch "addpath('examples/pucch'); export_NRPUCCH0_reference;"
.venv\Scripts\python -X utf8 -m pytest tests/matlab/test_NRPUCCH0_matlab.py --require-matlab
```

`export_NRPUCCH0_reference(outputFile)`的outputFile可省略，默认同目录JSON。HARQ空数组在JSON为[]、单bit可能为标量；比较器按位序还原为一维list；sr=-1与second_hop_prb=-1分别表示未配置SR/跳频。复数拆成real/imag，MATLAB列优先[T,Rx]对应Python[Rx,T]按C序恢复；序列12点按频率再符号排列。PRB始终相对BWP，索引向量是[port0,slot_symbol,carrier_k]零基坐标。

### R15与当前Toolbox扩展CP差异

TS38.211 V15.2.0 §6.3.2.2.2循环移位Gold寻址是固定14*slot；当前Toolbox默认按CP符号数寻址，extended使用12。脚本对序列生成的公开`nrPUCCH0`显式传normal CP，让序列阶段保持14寻址；物理RE、nrOFDMModulate/nrOFDMDemodulate仍用真实extended CP。Toolbox译码在已提取RE上也按14寻址适配。JSON同时保留未经适配的默认序列以检查版本差异，不隐瞒两者不同。[完整验证报告](../../documentation/validation/NRPUCCH0_validation.md)。

### 结果含义

默认示例中HARQ[1]、HARQ[1,0]+正SR、SR-only正SR均正确检测；负SR仅背景噪声，判DTX。接收机不将DTX强行解释为NACK。相关指标是无量纲0..1的功率归一化量，不是SNR、吞吐率或RSRP。所有公式变量、范围、单位及轴见三份类文档；只支持Format 0，其余格式待后续补充。




## 每步变换直接显示，不保存图片

示例入口的字段配置：

```python
from diagnostics import NRPlotConfig
plot_config=NRPlotConfig(enabled=True,stages=('case0.*',))
# 关闭：NRPlotConfig(enabled=False)
# 只接收：NRPlotConfig(enabled=True,stages=('case0.rx.*',))
# 四案例所有阶段：NRPlotConfig(enabled=True,stages=None)
```

`main(log,plot_config=None)`默认启用case0的28个阶段，分页为5个图窗；默认每窗6个面板。case0..case3依次为1bit HARQ、2bit HARQ+正SR、SR-only正SR、SR-only负SR。stages按完整阶段名匹配通配符，max_points和max_branches只限制显示密度，不改信号处理。非阻塞show在处理后直接显示，脚本末尾plt.show等待用户关闭窗口；要求GUI后端及plots可选依赖，不再强制Agg。

| 链路位置 | 阶段名（案例前缀如case0省略） |
|---|---|
| UCI/序列/幅度映射 | tx.uci_shift、tx.base_sequence、tx.cyclic_shift、tx.alpha、tx.mapped_grid |
| OFDM发射 | tx.symbol_phase、tx.phase_compensated_grid、tx.fft_spectrum、tx.ifft_useful、tx.cp_waveform |
| 时域信道 | channel.ta、channel.spatial、channel.path_delay、channel.cfo、channel.noise、channel.received |
| 接收同步 | rx.input_waveform、rx.cfo_corrected、rx.timing_corrected |
| OFDM解调 | rx.fft_windows、rx.fft_spectrum、rx.cropped_grid、rx.window_corrected_grid、rx.phase_corrected_grid |
| UCI检测 | rx.extracted_symbols、rx.correlated_constellation、rx.candidate_metrics、rx.decision |

波形图画I/Q/幅度；网格和频谱把平均分支功率dB与首分支相位rad并排显示，避免纯相位变换看不出区别。所有图像均在内存/图窗中，没有savefig或图像输出路径；关闭时不创建图窗、不保留绘图数组、不导入Matplotlib。已有数值JSON/NPZ保存行为继续保留，summary新增plotting字段和实际选中阶段名。

[配置每个字段](../../src/diagnostics/NRPlotConfig.md)、[绘图类接口及单位](../../src/diagnostics/NRStagePlotter.md)。


### 相关后的复平面/星座图

```python
plot_config=NRPlotConfig(enabled=True,stages=('case0.rx.correlated_constellation',))
```

显示最佳UCI候选的归一化复相关值：correlation=sum(y*conj(reference),axis=frequency)/12。y为[Rx,S,12]实际提取RE，reference为[S,12]单位模候选，输出[Rx,S]归一化复幅度。12是每符号参考能量，不是接收支路数；两个跳段不会先相干相加。图中横轴I、纵轴Q，标记区分Rx，S0/S1标注PUCCH内符号。固定信道下点接近beta*H，可能不在单位圆或QPSK固定点；F0的数据仍由m_cs区分。DTX时图标题注明只是噪声中的最佳假设，不表示已解出有效符号。

新数值字段correlation_symbols[Rx,S]和candidate_correlation_symbols[H,Rx,S]保存在NPZ；summary JSON不包含复数数组。绘图只显示，不保存PNG/SVG。

## PUCCH Format 1

运行`python examples/pucch/NRPUCCH1_demo.py`：1/2bit调制、OCC、DMRS→OFDM→两Rx复增益、延迟2采样点、CFO731Hz/初相0.23rad、SNR15dB噪声→同步补偿、DMRS信道估计、MRC、判决。main(log,plot_config=None)返回接收字典；log为ExampleLogger，plot_config为可选NRPlotConfig，默认显示，enabled=False禁用。不保存图像或数值文件。

[MATLAB导出](export_NRPUCCH1_reference.m)、[实际向量](NRPUCCH1_reference.json)、[比较脚本](compare_NRPUCCH1_reference.py)、[比较摘要](NRPUCCH1_comparison.json)保留68组普通CP/QPSK参考。`compare(write_report=True)`返回比较字典，默认写比较JSON，False只比较；直接运行脚本打印摘要。实际MATLAB参考覆盖网格、DMRS、波形和Python对MATLAB波形的判决；不是Toolbox接收机性能认证。详细边界见[验证报告](../../documentation/validation/NRPUCCH1_validation.md)。

## PUCCH Format 2

运行`python examples/pucch/NRPUCCH2_demo.py`：7位UCI→小块编码/速率匹配→加扰QPSK/DMRS→OFDM→两Rx增益、延迟2采样点、CFO731Hz/初相0.23rad、整slot SNR15dB加噪→DMRS估计/MRC→软解扰/ML译码。资源为3RB、两符号、符号8起始、RB1→6跳频。main(log,plot_config=None)接收ExampleLogger及可选NRPlotConfig，默认显示；enabled=False关闭，不保存图片或数值文件，返回接收字典。

[MATLAB导出](export_NRPUCCH2_reference.m)、[实际向量](NRPUCCH2_reference.json)、[比较脚本](compare_NRPUCCH2_reference.py)、[比较摘要](NRPUCCH2_comparison.json)。运行`python examples/pucch/compare_NRPUCCH2_reference.py`复验。compare(write_report=True)默认写比较JSON并返回摘要，False不写文件。MATLAB需R2024a/5G Toolbox，向量由nrUCIEncode、nrPUCCH2、nrPUCCHDMRS及nrOFDMModulate真实生成。

仅3～11位UCI完整闭环，不实现Polar。收发接口限制码率≤0.6，超出需增加RB；原始HARQ/SR/CSI字段组合、调度码率选择不在本例。图包含编码位、QPSK、网格、OFDM、信道波形、信道估计、均衡星座和软比特，只显示不保存。

## 当前F2长UCI及F3

运行`python examples/pucch/NRPUCCH2_Polar_demo.py`和`python examples/pucch/NRPUCCH3_demo.py`。两者main(log,plot_config=None)接收ExampleLogger与可选NRPlotConfig，默认显示，enabled=False关闭，返回含bits/crc_ok的接收字典，不保存图像或数值产物。32位UCI经过时域增益、延迟2采样点、CFO731Hz和SNR15dB信道后正确译码及CRC通过；F3含DFT预编码/IDFT解扩。

F2当前56组参考包含Polar长UCI；此前36组/仅3～11位为历史首版。F3实际参考：export_NRPUCCH3_reference.m、NRPUCCH3_reference.json、compare_NRPUCCH3_reference.py、NRPUCCH3_comparison.json。比较脚本compare(write_report=True)默认写摘要JSON，False仅比较，错误时assert失败。协议与未验证边界见[最新报告](../../documentation/validation/NRPUCCH3_validation.md)。

## PUCCH Format 4

运行`python examples/pucch/NRPUCCH4_demo.py`：SF2/OCC1/32位Polar、SF4/OCC3/7位小块码两个案例，共享完整UCI编码→OCC扩频→12点DFT→OFDM→两Rx信道增益、延迟2采样点、CFO731Hz、SNR15dB→IDFT/OCC解扩/译码。main(log,plot_config=None)接收ExampleLogger及可选NRPlotConfig，默认显示，enabled=False禁用；返回两个案例结果list[dict]，包含sf/occ/bits_match及接收机输出。只显示，不保存图片或数值产物。

[实际MATLAB导出](export_NRPUCCH4_reference.m)、[参考向量](NRPUCCH4_reference.json)、[比较脚本](compare_NRPUCCH4_reference.py)、[比较摘要](NRPUCCH4_comparison.json)。compare(write_report=True)默认写摘要JSON，False只比较；直接运行打印精简误差统计。132组覆盖全部OCC、两种调制及4～14符号。细节与未验证场景见[验证报告](../../documentation/validation/NRPUCCH4_validation.md)。

## 100MHz / 30kHz测试

- [NRPUCCH0_100MHz_30kHz_demo.py](NRPUCCH0_100MHz_30kHz_demo.py)：PRB272，符号12/13，1bit HARQ。
- [NRPUCCH1_100MHz_30kHz_demo.py](NRPUCCH1_100MHz_30kHz_demo.py)：PRB272，14符号，2bit UCI。
- [NRPUCCH2_100MHz_30kHz_demo.py](NRPUCCH2_100MHz_30kHz_demo.py)：PRB269～272，2符号，7bit UCI。
- [NRPUCCH3_100MHz_30kHz_demo.py](NRPUCCH3_100MHz_30kHz_demo.py)：PRB261～272，14符号，32bit Polar UCI。
- [NRPUCCH4_100MHz_30kHz_demo.py](NRPUCCH4_100MHz_30kHz_demo.py)：PRB272，SF2/OCC1，32bit Polar UCI。

统一使用FR1 273PRB/4096FFT/122.88MS/s；run_case(plot_config=None)关闭绘图，直接运行脚本默认显示。结果包含passed、公共元信息、resource、sent及result；图片不保存。每例独立MATLAB参考/比较文件同目录，名称为<类名>_100MHz_30kHz_reference.json和_comparison.json。

共同入口：[MATLAB导出](../common/export_NR100MHz_30kHz_reference.m)、[独立比较](../common/compare_NR100MHz_30kHz_reference.py)、[用例矩阵及边界](../../documentation/validation/NR100MHz_30kHz_validation.md)。

## 100MHz / 30kHz测试

- [NRPUCCH0_100MHz_30kHz_demo.py](NRPUCCH0_100MHz_30kHz_demo.py)：PRB272，符号12/13，1bit HARQ。
- [NRPUCCH1_100MHz_30kHz_demo.py](NRPUCCH1_100MHz_30kHz_demo.py)：PRB272，14符号，2bit UCI。
- [NRPUCCH2_100MHz_30kHz_demo.py](NRPUCCH2_100MHz_30kHz_demo.py)：PRB269～272，2符号，7bit UCI。
- [NRPUCCH3_100MHz_30kHz_demo.py](NRPUCCH3_100MHz_30kHz_demo.py)：PRB261～272，14符号，32bit Polar UCI。
- [NRPUCCH4_100MHz_30kHz_demo.py](NRPUCCH4_100MHz_30kHz_demo.py)：PRB272，SF2/OCC1，32bit Polar UCI。

统一使用FR1 273PRB/4096FFT/122.88MS/s；run_case(plot_config=None)关闭绘图，直接运行脚本默认显示。结果包含passed、公共元信息、resource、sent及result；图片不保存。每例独立MATLAB参考/比较文件同目录，名称为<类名>_100MHz_30kHz_reference.json和_comparison.json。

共同入口：[MATLAB导出](../common/export_NR100MHz_30kHz_reference.m)、[独立比较](../common/compare_NR100MHz_30kHz_reference.py)、[用例矩阵及边界](../../documentation/validation/NR100MHz_30kHz_validation.md)。

## 100MHz / 30kHz测试

- [NRPUCCH0_100MHz_30kHz_demo.py](NRPUCCH0_100MHz_30kHz_demo.py)：PRB272，符号12/13，1bit HARQ。
- [NRPUCCH1_100MHz_30kHz_demo.py](NRPUCCH1_100MHz_30kHz_demo.py)：PRB272，14符号，2bit UCI。
- [NRPUCCH2_100MHz_30kHz_demo.py](NRPUCCH2_100MHz_30kHz_demo.py)：PRB269～272，2符号，7bit UCI。
- [NRPUCCH3_100MHz_30kHz_demo.py](NRPUCCH3_100MHz_30kHz_demo.py)：PRB261～272，14符号，32bit Polar UCI。
- [NRPUCCH4_100MHz_30kHz_demo.py](NRPUCCH4_100MHz_30kHz_demo.py)：PRB272，SF2/OCC1，32bit Polar UCI。

统一使用FR1 273PRB/4096FFT/122.88MS/s；run_case(plot_config=None)关闭绘图，直接运行脚本默认显示。结果包含passed、公共元信息、resource、sent及result；图片不保存。每例独立MATLAB参考/比较文件同目录，名称为<类名>_100MHz_30kHz_reference.json和_comparison.json。

共同入口：[MATLAB导出](../common/export_NR100MHz_30kHz_reference.m)、[独立比较](../common/compare_NR100MHz_30kHz_reference.py)、[用例矩阵及边界](../../documentation/validation/NR100MHz_30kHz_validation.md)。

## 100MHz / 30kHz测试

- [NRPUCCH0_100MHz_30kHz_demo.py](NRPUCCH0_100MHz_30kHz_demo.py)：PRB272，符号12/13，1bit HARQ。
- [NRPUCCH1_100MHz_30kHz_demo.py](NRPUCCH1_100MHz_30kHz_demo.py)：PRB272，14符号，2bit UCI。
- [NRPUCCH2_100MHz_30kHz_demo.py](NRPUCCH2_100MHz_30kHz_demo.py)：PRB269～272，2符号，7bit UCI。
- [NRPUCCH3_100MHz_30kHz_demo.py](NRPUCCH3_100MHz_30kHz_demo.py)：PRB261～272，14符号，32bit Polar UCI。
- [NRPUCCH4_100MHz_30kHz_demo.py](NRPUCCH4_100MHz_30kHz_demo.py)：PRB272，SF2/OCC1，32bit Polar UCI。

统一使用FR1 273PRB/4096FFT/122.88MS/s；run_case(plot_config=None)关闭绘图，直接运行脚本默认显示。结果包含passed、公共元信息、resource、sent及result；图片不保存。每例独立MATLAB参考/比较文件同目录，名称为<类名>_100MHz_30kHz_reference.json和_comparison.json。

共同入口：[MATLAB导出](../common/export_NR100MHz_30kHz_reference.m)、[独立比较](../common/compare_NR100MHz_30kHz_reference.py)、[用例矩阵及边界](../../documentation/validation/NR100MHz_30kHz_validation.md)。

## 100MHz / 30kHz测试

- [NRPUCCH0_100MHz_30kHz_demo.py](NRPUCCH0_100MHz_30kHz_demo.py)：PRB272，符号12/13，1bit HARQ。
- [NRPUCCH1_100MHz_30kHz_demo.py](NRPUCCH1_100MHz_30kHz_demo.py)：PRB272，14符号，2bit UCI。
- [NRPUCCH2_100MHz_30kHz_demo.py](NRPUCCH2_100MHz_30kHz_demo.py)：PRB269～272，2符号，7bit UCI。
- [NRPUCCH3_100MHz_30kHz_demo.py](NRPUCCH3_100MHz_30kHz_demo.py)：PRB261～272，14符号，32bit Polar UCI。
- [NRPUCCH4_100MHz_30kHz_demo.py](NRPUCCH4_100MHz_30kHz_demo.py)：PRB272，SF2/OCC1，32bit Polar UCI。

统一使用FR1 273PRB/4096FFT/122.88MS/s；run_case(plot_config=None)关闭绘图，直接运行脚本默认显示。结果包含passed、公共元信息、resource、sent及result；图片不保存。每例独立MATLAB参考/比较文件同目录，名称为<类名>_100MHz_30kHz_reference.json和_comparison.json。

共同入口：[MATLAB导出](../common/export_NR100MHz_30kHz_reference.m)、[独立比较](../common/compare_NR100MHz_30kHz_reference.py)、[用例矩阵及边界](../../documentation/validation/NR100MHz_30kHz_validation.md)。

- [NRPUCCH0新手导读](../../src/pucch/NRPUCCH0.md)：生成步骤、时频位置、配置差异、接收算法与图例。

- [NRPUCCH1新手导读](../../src/pucch/NRPUCCH1.md)：生成步骤、时频位置、配置差异、接收算法与图例。

- [NRPUCCH2新手导读](../../src/pucch/NRPUCCH2.md)：生成步骤、时频位置、配置差异、接收算法与图例。

- [NRPUCCH3新手导读](../../src/pucch/NRPUCCH3.md)：生成步骤、时频位置、配置差异、接收算法与图例。

- [NRPUCCH4新手导读](../../src/pucch/NRPUCCH4.md)：生成步骤、时频位置、配置差异、接收算法与图例。

文档配图：[NRPUCCH0_documentation.png](NRPUCCH0_documentation.png)、[NRPUCCH1_documentation.png](NRPUCCH1_documentation.png)、[NRPUCCH2_documentation.png](NRPUCCH2_documentation.png)、[NRPUCCH3_documentation.png](NRPUCCH3_documentation.png)、[NRPUCCH4_documentation.png](NRPUCCH4_documentation.png)。由[公共绘图脚本](../common/plot_NRChannel_documentation.py)生成；默认只显示，显式`--save`才导出文档PNG。
## 不同符号数的时域对照

[NRPUCCH_symbol_counts_demo.py](NRPUCCH_symbol_counts_demo.py) 默认运行 13 组。所有案例使用 60 kHz SCS，把资源放在 slot 末尾，固定 PRB 与 UCI、关闭跳频，便于逐组比较符号数的影响。

| 格式 | 普通 CP 可演示的符号数 | 扩展 CP 可演示的符号数 | 默认对照 |
|---|---|---|---|
| F0、F2 | 1、2 | 1、2 | 1 和 2 |
| F1、F3、F4 | 4～14 | 4～12 | 4、7 和当前 slot 的最大值 |

此表依据 TS 38.211 V15.2.0 §6.3.2.1 原表 6.3.2.1-1，扩展 CP 的上限由同版本 §4.3.2 原表 4.3.2-2 的 12 符号 slot 推得。见[协议索引](../../documentation/spec_manifest.md)。

```powershell
# 五种格式，普通 CP，直接显示图形
.venv\Scripts\python.exe -X utf8 examples/pucch/NRPUCCH_symbol_counts_demo.py
# 只看 Format 3 的 7 符号波形
.venv\Scripts\python.exe -X utf8 examples/pucch/NRPUCCH_symbol_counts_demo.py --format 3 --symbols 7
# 扫描扩展 CP 下的全部符号数，只显示终端结果
.venv\Scripts\python.exe -X utf8 examples/pucch/NRPUCCH_symbol_counts_demo.py --cp extended --all-lengths --no-plot
```

左图以蓝色标记承载 UCI 的 RE、橙色标记 DM-RS。F0 通过序列循环移位携带 UCI，图中没有独立的 DM-RS。F1 的 DM-RS 和数据按符号交替，F2 在同一符号内按子载波分开，F3/F4 的 DM-RS 占整符号。右图画出发射波形 I 分量，阴影覆盖分配时段，虚线按实际 CP 加有用部分的样点数标出符号边界。图直接显示。

每个案例经过 2 样点延迟、731 Hz CFO 和 22 dB SNR 噪声，在已知延迟和 CFO 条件下解码。终端会列出起始符号、占用时长、两类 RE 数量和解码结果。新增矩阵是 Python 收发回归，独立 MATLAB 覆盖见各格式的验证报告。
