# NRPUSCHTransmitter

[源码](NRPUSCHTransmitter.py)。TB→NRULSCHCode CRC/LDPC/全缓冲速率匹配→加扰/QAM/DMRS→NRGrid→NROFDM完整slot。固定TS38.212 V15.2.0 §6.2及TS38.211 V15.2.0 §6.3.1/§6.4.1.1/§5.3.1。

| 字段 | 含义、范围、示例 |
|---|---|
| resource | 必须NRPUSCH，1～4层单码字资源 |
| target_code_rate=.5 | MCS给定目标R，有限0.0001..0.95，用于BG选择 |
| redundancy_version=0 | RV整数0..3 |
| carrier_frequency_hz=0 | 有限非负载频Hz，用于NR符号相位补偿，例3.5e9 |
| plot_config=None | 可选NRPlotConfig，None关闭；例NRPlotConfig(enabled=True,channel='PUSCH') |

构造/`__post_init__`校验资源、公共编码/OFDM和绘图配置。`transmit(bits,beta=1,*,plotter=None)`输入整数二进制TB[A]（16..8424且8位对齐，单码块限制）、非负线性幅度beta及可选共享NRStagePlotter。保护检查(A+CRC)/G≤0.95，错误输入/容量不足抛异常；该检查不代替真实MCS/TBS调度选择。

输出dict：waveform为complex[n_layers,T]完整slot波形；grid为n_layers端口NRGrid；coded_bits为int8[G]；base_graph为1/2；lifting_size为Z。T=cell.samples_per_slot，G=resource.coded_length，所有复幅度归一化，无绝对功率标定。

图阶段tx.coded_bits、tx.modulation（按Layer图例）、tx.grid及OFDM相位/FFT/IFFT/CP步骤。独立调用非阻塞show，共享绘图器由调用方show，禁用不导入Matplotlib；只显示，不保存图像。

```python
from cell import NRCell
from pusch import NRPUSCH, NRPUSCHTransmitter
r = NRPUSCH(NRCell(n_size_grid=12), n_symbols=12)
sent = NRPUSCHTransmitter(r).transmit([0,1]*128)
```

多层层映射由NRPUSCH.generate完成，码字符号轮流分到各层；默认返回每层一个OFDM波形，未自动选择物理预编码矩阵。n_layers与逻辑端口数一致，与接收天线数不同。MIMO示例使用单位预编码，外部有效信道矩阵在时域混合各层波形。单码块时E=G，因此复用同一UL-SCH编码算子，G由资源保证是Qm*n_layers的整数倍。

## 新手处理流程与资源图入口

上行共享信道承载业务传输块：CRC → LDPC → 速率匹配/RV → 数据加扰 → QAM → 1～4层映射 → DMRS与数据RE映射 → 普通OFDM。编码位数由可用数据RE、层数与调制阶数决定，不能用整个RB矩形面积直接计算。当前传输块长度和目标码率显式输入，不自动执行MCS/TBS调度。

[NRPUSCH的时频位置、长度、配置变化及图例](NRPUSCH.md)与[统一坐标/采样点换算](../../documentation/channel_walkthrough.md)提供完整阅读顺序。当前类的输入输出单位、形状及异常约束以上文字段/API节为准。


资源配置 `ptrs_config` 后，`transmit()` 按扣除 PT-RS RE 后的 `coded_length` 编码，并在同一网格中写入数据、DM-RS 和 PT-RS。`beta` 对三者统一缩放。位置及允许的配置见资源类文档。
