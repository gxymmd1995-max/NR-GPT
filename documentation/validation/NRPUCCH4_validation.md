# PUCCH Format 4验证

固定TS38.211 V15.2.0 §6.3.2.6、表6.3.2.6.3-1/-2、§6.4.1.3.3及表6.4.1.3.3.1-1/6.4.1.3.3.2-1；编码为TS38.212 V15.2.0 §6.3.1及原表6.3.1.4-1。发送实现频域OCC扩频后12点单位化DFT，接收实现12点单位化IDFT后共轭OCC分块平均。

## 实际MATLAB独立比对

MATLAB 24.1.0.2537033 (R2024a)，5G Toolbox24.1。实际运行[导出脚本](../../examples/pucch/export_NRPUCCH4_reference.m)，调用nrUCIEncode、nrPUCCH4、nrPUCCHDMRS、相关资源索引、nrOFDMModulate，产生[真实向量](../../examples/pucch/NRPUCCH4_reference.json)。完整输入、编码位、网格、两Rx时域波形和实际环境均保留，不使用Python输出冒充MATLAB。

132例覆盖4～14符号、SF2的全部2个OCC、SF4的全部4个OCC，以及QPSK/π/2-BPSK；跳频及额外DMRS配置变化，涵盖小块码和Polar。载波6RB、NStartGrid10、BWP起点11/大小4、PRB1→3、普通CP/30kHz、slot3、数据ID731、DMRS ID271、RNTI4321，两Rx平坦增益0.7+0.4j与-0.3+0.6j。

[比较结果](../../examples/pucch/NRPUCCH4_comparison.json)：编码位差异0，实际MATLAB时域波形的Python解码差异0，Polar CRC全部通过。最大网格绝对误差1.3145715729848181e-14，最大时域绝对误差2.1334277879468754e-16，单位均为归一化复幅度，容限1e-10。SHA256覆盖实际参考、生成/比较脚本、F4实现及相关共享依赖。

OCC顺序精确依据原表：SF4索引1为连续块系数[1,-j,-1,j]，索引3为[1,j,-1,-j]；不能因其他顺序也正交而认为编号可互换。DMRS另按原表使用m0=[0,6,3,9]。MATLAB比较同时核对数据和DMRS，不以只检查收发自洽代替标准验证。

## 单元测试与示例

新增39项单元测试及1个MATLAB入口；全套819项测试通过。覆盖OCC原表顺序、正交性、扩频/解扩逆变换、跨OCC抑制、DMRS循环移位、非法配置/码率、Polar及奇数E小块码、普通/扩展CP、两种调制和所有OCC的时域噪声/CFO/延迟闭环，以及零输入DTX。四用户同资源案例将各自时域波形经不同复增益后叠加，再统一加噪，四个接收实例从同一波形正确恢复各自比特；该多用户案例目前只有Python测试，未声称MATLAB独立多用户验证。

[示例](../../examples/pucch/NRPUCCH4_demo.py)分别运行SF2/OCC1/32位Polar和SF4/OCC3/7位小块码；时域波形经过延迟2采样点、CFO731Hz、初相0.23rad和SNR15dB，显式已知同步补偿后比特全部恢复，Polar CRC通过，小块码无CRC标志。默认阶段图直接显示，不保存图像或数值文件。

```powershell
.venv\Scripts\python -X utf8 examples/pucch/NRPUCCH4_demo.py
.venv\Scripts\python -X utf8 examples/pucch/compare_NRPUCCH4_reference.py
.venv\Scripts\python -X utf8 -m pytest --require-matlab -q
```

## 边界

普通CP单用户MATLAB参考为无噪、已同步波形。扩展CP、噪声/频偏/净时延补偿、四用户复用目前仅Python链路测试；未覆盖独立MATLAB这些场景。接收每跳假设时间和频率近似平坦，不含强频选均衡、时间插值、盲同步或联合多用户均衡。DTX门限不保证恒定虚警率，detected与crc_ok独立；Polar为PC约束SC，非CRC辅助SCL。

公共NRUCICode调整为允许单码块奇数E，支持SF4 π/2-BPSK的每数据符号3位。双码块仍要求偶数E；F4单RB资源无法达到该分段容量，F2/F3已有双块偶数E规则不变。既有UCI/F2/F3实际参考重新比较通过并刷新实现哈希。未创建Git提交或推送。
