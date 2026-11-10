# NRPUCCH4Receiver

[源码](NRPUCCH4Receiver.py)。时域接收→已知同步补偿→OFDM→每跳DMRS平坦信道估计→MRC→12点IDFT→共轭OCC解扩/除SF→QPSK或π/2-BPSK软解映射→解扰→公共小块/Polar译码及CRC。发送/解扩公式与变量见[资源文档F4-1](NRPUCCH4.md)，其依据TS38.211 V15.2.0 §6.3.2.6及§6.4.1.3.3；接收处理为项目工程算法，不是规范指定的唯一接收机。

| 字段 | 含义、范围、示例 |
|---|---|
| resource | NRPUCCH4，不含实际发送位 |
| n_bits=3 | 期待UCI位数，公共范围3..1706；含CRC码率≤0.6，F4容量会进一步限制 |
| carrier_frequency_hz=0 | 有限非负Hz，与发射一致 |
| detection_threshold=.1 | DMRS拟合能量比，有限0..1，严格大于才检测 |
| plot_config=None | 可选NRPlotConfig，None关闭 |

构造/`__post_init__`验证上述参数及公共UCI资源。`receive(waveform,*,known_frequency_offset_hz=0,known_initial_phase_rad=0,known_delay_samples=0,cp_fraction=1,plotter=None)`要求有限complex[Rx,T]完整当前slot；Rx/T严格匹配cell。CFO（Hz）、初相（rad）先取负补偿，再按净延迟整数采样点提前；正延迟意味着接收波形滞后。cp_fraction为CP内FFT窗比例0..1；plotter为可选共享NRStagePlotter。已知参数不是估计结果，非法类型/值/形状抛校验异常。

每跳全部DMRS和12频点平均估计每Rx增益，假设该跳时间/频率近似平坦。未归一化MRC投影经单位化IDFT后，以当前用户OCC共轭分块平均；这一输出形成软分数，保留不同支路/跳的可靠度权重。显示的均衡星座再除sum(abs(h)^2)，≤1e-20时置0。软值仅与等白噪声LLR成比例，无独立噪声方差标定。

输出dict：bits为A位list或未检测None；crc_ok在Polar时bool，小块/未检测时None；detected为严格bool；metric为无量纲0..1；soft_bits为float[E]；equalized_symbols为complex[S*12/SF]，已完成OCC解扩；channel_estimates为complex[S,Rx]，每个数据符号重复其跳估计；rx_grid为complex[Rx,slot符号数,载波子载波数]。复幅度均归一化。

检测指标为平坦DMRS估计重建能量/实际DMRS接收能量，clip至0..1，零能量为0。detected只表示检测到兼容参考，不能替代crc_ok；CRC失败仍返回候选位。小块码没有CRC，不能把None理解成CRC通过。门限未校准恒定虚警率，多用户总功率会使单用户指标下降。

绘图rx.idft_constellation实际显示IDFT加OCC解扩后的调制点；rx.soft_bits显示解扰软值，并有OFDM内部阶段；只显示不保存。未实现盲同步、强频选均衡、DMRS时间插值、任意近远效应下的联合用户接收或CRC辅助SCL。Polar为PC约束SC，低SNR性能有限。

```python
from cell import NRCell
from pucch import NRPUCCH4, NRPUCCH4Transmitter, NRPUCCH4Receiver
r = NRPUCCH4(NRCell(n_size_grid=6), spreading_factor=4, occ_index=3)
wave = NRPUCCH4Transmitter(r).transmit([1,0,1,1,0,0,1])['waveform']
assert NRPUCCH4Receiver(r,7).receive(wave)['bits'] == [1,0,1,1,0,0,1]
```

## 新手处理流程与资源图入口

先按跳段用DMRS估计平坦增益、跨Rx合并，再12点IDFT；乘本用户OCC共轭，重排为[SF,12/SF]并沿SF维平均，恢复每用户调制符号，然后解调软值、解扰和UCI译码。配置不同OCC是可分离的必要设计之一，实际分离仍受信道时频变化、同步误差和近远效应影响。

[NRPUCCH4的时频位置、长度、配置变化及图例](NRPUCCH4.md)与[统一坐标/采样点换算](../../documentation/channel_walkthrough.md)提供完整阅读顺序。当前类的输入输出单位、形状及异常约束以上文字段/API节为准。
