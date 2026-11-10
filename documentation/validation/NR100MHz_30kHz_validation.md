# FR1 100MHz、30kHz：全部已实现信道用例

## 共同配置与规范

固定TS38.104 V15.2.0 §5.3.2、原表5.3.2-1（原文PDF第27页）：FR1/100MHz/30kHz对应273PRB。273*12*30kHz=98.28MHz为资源网格占用带宽，100MHz为标称RF信道带宽，两者不混同。该表不表示每个控制信道都必须占满100MHz。

所有用例NRCell(n_cell_id=17,n_size_grid=273,subcarrier_spacing_khz=30,n_rx_antennas=2)，普通CP、NStartGrid/BWP起点0、完整BWP273RB、slot0。按平台FFT选择规则得4096点FFT、122.88MS/s、每slot61440样点/0.5ms；采样率不是100MS/s。时序依据TS38.211 V15.2.0 §4.2/§4.3/§5.3，FFT尺寸为平台派生选择，不冒充协议强制值。

## 独立用例

| 类 | 分配/输入 | 脚本 |
|---|---|---|
| NRPUCCH0 | PRB272，符号12/13，1bit HARQ | [NRPUCCH0_100MHz_30kHz_demo.py](../../examples/pucch/NRPUCCH0_100MHz_30kHz_demo.py) |
| NRPUCCH1 | PRB272，14符号，2bit UCI | [NRPUCCH1_100MHz_30kHz_demo.py](../../examples/pucch/NRPUCCH1_100MHz_30kHz_demo.py) |
| NRPUCCH2 | PRB269～272，2符号，7bit UCI | [NRPUCCH2_100MHz_30kHz_demo.py](../../examples/pucch/NRPUCCH2_100MHz_30kHz_demo.py) |
| NRPUCCH3 | PRB261～272，14符号，32bit Polar UCI | [NRPUCCH3_100MHz_30kHz_demo.py](../../examples/pucch/NRPUCCH3_100MHz_30kHz_demo.py) |
| NRPUCCH4 | PRB272，SF2/OCC1，32bit Polar UCI | [NRPUCCH4_100MHz_30kHz_demo.py](../../examples/pucch/NRPUCCH4_100MHz_30kHz_demo.py) |
| NRPUSCH | PRB0～272，12符号，1024bit TB，单层QPSK | [NRPUSCH_100MHz_30kHz_demo.py](../../examples/pusch/NRPUSCH_100MHz_30kHz_demo.py) |
| NRPDSCH | PRB0～272，12符号，1024bit TB，单层QPSK | [NRPDSCH_100MHz_30kHz_demo.py](../../examples/pdsch/NRPDSCH_100MHz_30kHz_demo.py) |
| NRPDCCH | 45个六RB组/270RB CORESET，2符号，AL4显式候选，32bit DCI | [NRPDCCH_100MHz_30kHz_demo.py](../../examples/pdcch/NRPDCCH_100MHz_30kHz_demo.py) |
| NRPRACH | A1，RA间隔30kHz，频域起点261，前导7 | [NRPRACH_100MHz_30kHz_demo.py](../../examples/prach/NRPRACH_100MHz_30kHz_demo.py) |
| NRSRS | c_srs=63/b_srs=0，272RB，comb2/单端口，slot末符号 | [NRSRS_100MHz_30kHz_demo.py](../../examples/srs/NRSRS_100MHz_30kHz_demo.py) |

上述10例为新增SSB前已实现的PUCCH F0～F4、PUSCH/PDSCH/PDCCH、PRACH和SRS。后续SSB/PBCH已新增独立100MHz入口及真实MATLAB案例，见[SSB验证](NRSSB_validation.md)及examples/ssb/NRSSB_100MHz_30kHz_demo.py。PUCCH/PDCCH保持各自规范资源宽度；共享信道覆盖全部273RB，SRS带宽按固定R15原表6.4.1.4.3-1选272RB。PRACH有自己的FFT/间隔；本例显式选RA30kHz，并非从载波隐式继承。

## 运行与判定

```powershell
.venv\Scripts\python -X utf8 examples/pusch/NRPUSCH_100MHz_30kHz_demo.py
.venv\Scripts\python -X utf8 -m pytest tests/integration/test_NR100MHz_30kHz.py -q
.venv\Scripts\python -X utf8 examples/common/compare_NR100MHz_30kHz_reference.py
```

每个run_case(plot_config=None)在None时禁用绘图；直接运行脚本时用NRPlotConfig(enabled=True,channel=...)显示实际变换步骤，只显示、不保存图片。ExampleLogger日志放对应模块目录并Git忽略。返回字典：channel为类名；bandwidth_hz为标称100000000；scs_khz=30；n_prbs=273；n_fft=4096；sample_rate_hz=122880000；passed为链路判定；resource为资源实例、sent为发送波形/网格/编码诊断、result为接收结果。数组轴及单位沿用对应类.md。

时域扰动为两Rx复增益[0.7+0.4j,-0.3+0.6j]、2采样点净延迟、731Hz频偏、0.23rad初相及按整段每支路功率定义的25dB SNR噪声，seed42。普通信道接收端显式补偿同步后判比特/CRC；PRACH仅补CFO，由相关恢复前导7及2样点延迟；SRS先补全部同步，再由SRS接收机确认0样点剩余延迟。没有把真实时延提供给PRACH估计器。

PUSCH/PDSCH的1024bit TB是显式给定的单码块测试输入，不执行MCS/TBS自动调度；不能将满带宽分配但低净码率的用例当吞吐率或峰值性能测试。当前矩阵每类一组代表性参数，未覆盖全部格式/层数/调制的笛卡尔积。

## MATLAB真实独立验证

真实MATLAB 24.1.0.2537033 (R2024a)/5G Toolbox24.1运行[共同导出脚本](../../examples/common/export_NR100MHz_30kHz_reference.m)，调用对应nrPUCCH、nrPUSCH/PDSCH、nrPDCCH、nrPRACH、nrSRS及编码/OFDM公开函数。固定上述载波、Nfft4096、Windowing=0，PRACH使用独立nrPRACHOFDMModulate。未用Python生成MATLAB向量。参数常量和payload构造保留在可复现脚本，各例参考另保存环境/输入位/编码位、网格及波形信息。

每个模块目录保留<类名>_100MHz_30kHz_reference.json与_comparison.json。参考保留全部活动RE的零基MATLAB线性索引/复值、所有编码位、2048个均匀分布的时域样点探针、整段样点数及能量；**不保存完整时域波形**。比较完整非零RE集合和值、编码位、探针和总能量，不能将探针对齐表述为逐样点全波形验证或MATLAB接收机验证。带噪闭环来自Python独立时域测试，MATLAB向量为无扰动发送基准。

10例全部通过：最大RE误差约4.75e-11，时域探针最大误差约2.81e-13；归一化RE容差1e-9、波形探针1e-10、整段能量相对误差1e-9。完整编码位与非零坐标必须精确相等。JSON报告保存环境、逐项指标及实现/输入SHA256。

独立测试入口tests/matlab/test_NR100MHz_30kHz_matlab.py；--require-matlab要求真实参考存在，缺失不能冒充通过。原有其他带宽参考保持不变。本轮全仓1152项测试通过，3559条语句与1052个分支全部覆盖，综合覆盖率100.00%。本轮不创建Git提交或推送。
