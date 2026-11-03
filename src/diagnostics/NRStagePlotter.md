# NRStagePlotter：实际处理阶段的交互绘图

[源码](NRStagePlotter.py)是通用诊断类，按配置快照记录实际变换结果并分页显示。不调用savefig、不访问图片输出目录、不写PNG/SVG。默认关闭；仅绘图时延迟导入Matplotlib，保持纯数值运行不依赖绘图包。辅助基序列图由与发送端相同u的零循环移位公共函数生成，明确标为Diagnostic；其他图来自链路实际中间数组。

## 字段、属性与方法

| 名称 | 含义和范围 | 单位/维度/示例 |
|---|---|---|
| config | NRPlotConfig；构造参数None会创建默认关闭配置 | 配置对象，`NRStagePlotter(NRPlotConfig(enabled=True))` |
| prefix='' | 阶段名前缀，必须str；空字符串不添加前缀 | 例如case0，tx.cp_waveform成为case0.tx.cp_waveform |
| _records | 内部快照列表，依调用顺序保存名称、数组、类型、标题、轴名和标签 | 不对外暴露；关闭/未选中不复制数组 |
| stages | 只读阶段名tuple，不含内部数组 | 实际已记录的完整名称列表 |
| __init__(config=None,prefix='') | 校验配置与前缀，创建空记录列表 | 错误TypeError |
| record(stage,values,*,kind='waveform',title='',xlabel='Sample',ylabel='Normalized amplitude',labels=None) | 过滤阶段名，选中才校验并复制values | stage/title/xlabel/ylabel为显示文本；labels长度须等于数组末轴 |
| figures() | 创建内存Figure列表，不直接显示、不保存；每次调用创建新Figure | 无记录返回[]；调用方负责在不再使用时关闭 |
| show(*,block=False) | 调用figures后plt.show(block=block)直接显示 | 默认非阻塞；返回Figure列表；无记录不导入Matplotlib |

错误数组轴、非有限值、未知kind或标签长度不匹配报ValueError；Matplotlib/GUI依赖仅在实际绘制有记录的数据时需要。配置为冻结值对象，若要改变选项，创建新配置和新收集器。

## 绘图类型与轴

| kind | 输入意义 | 显示方法和单位 |
|---|---|---|
| waveform | 有限[N]或[B,N]复波形 | I/Q/幅度曲线；横轴为样点索引，纵轴归一化幅度；最多max_points、max_branches，仅影响可视化 |
| sequence | 有限[N]或[B,N]复序列 | 同上，但调用者标明序列点/RE索引；空序列说明DTX，不伪造数据 |
| grid | 有限[B,L,K]复网格/频谱，三轴均非空 | 左图各分支平方模平均的dB，右图B0相位rad，并排不遮挡数据；横轴slot符号，纵轴载波子载波或明确注明的FFT数组号 |
| constellation | 有限[N]或[B,N]复相关结果 | I/Q等比例散点；标记区分Rx，labels可标出S0/S1等符号号；不强制幅度/相位归一化 |
| metric | 有限[N]分数/相位参数 | 柱状图，labels指定候选或判决量；纵轴由调用者明确为无量纲、移位号或rad |

网格显示采用项目诊断换算：power=mean(abs(grid)**2,axis=0)，dB=10*log10(max(power,1e-12))；不是协议原公式。power为[L,K]归一化功率，1e-12是绘图下限，dB相对单位功率不是dBm。相位为angle(grid[0])，范围[-pi,pi] rad，零幅度位置遮罩。网格功率无法显示纯相位旋转，因此额外并排相位图。

波形绘图用等距索引选点，横轴仍为原始样点号。该显示抽样不是重采样/滤波，不用于估计信号带宽或改变FFT输入；实际数值仍以完整数组处理。多个符号的有效IFFT/FFT窗会无CP拼接，标题会注明此坐标不同于含CP的slot时间轴。

## 共享整条链路的收集器

```python
from diagnostics import NRPlotConfig,NRStagePlotter
from cell import NRCell
from pucch import NRPUCCH0,NRPUCCH0Transmitter,NRPUCCH0Receiver

resource=NRPUCCH0(NRCell(n_size_grid=6),start_symbol=10,n_symbols=2)
plotter=NRStagePlotter(NRPlotConfig(enabled=True),prefix='case0')
sent=NRPUCCH0Transmitter(resource).transmit([1],plotter=plotter)
result=NRPUCCH0Receiver(resource).receive(sent['waveform'],plotter=plotter)
figures=plotter.show(block=False)
assert result['harq_ack']==[1]
```

传入共享plotter时收发类不自行显示，等链路完成再统一show；不传plotter时，各类按自己的plot_config字段收集并非阻塞显示。用户独立脚本最后可用`plt.show()`等待关闭图窗。仅绘图开关改变时，同一发送波形和接收判决必须保持相同，单测对此作逐元素核对。
