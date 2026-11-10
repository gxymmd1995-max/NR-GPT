# SSB/PBCH及BCH首版验证

## 固定协议与实现范围

TS38.211 V15.2.0 §7.3.3（PBCH物理加扰/QPSK）、§7.4.1.4（DMRS）、§7.4.2（PSS/SSS）、§7.4.3及原表7.4.3.1-1（240×4映射）；定向读取原文PDF第82/90/93～95页。TS38.212 V15.2.0 §7.1.1～5及原表7.1.1-1/7.1.2-1（载荷/时序交织/加扰、CRC24C、K56/N512/E864 Polar），原文PDF第68～70页。未使用后续版本功能。

新增src/ssb三类及common/NRBCHCode。PSS127/SSS127/PBCH432/DMRS144/规范置零130，共960RE；映射保留整个SSB，避免其他owner占用零位置。支持FR1同间隔15/30kHz、Lmax4/8及FR2同间隔120/240kHz、Lmax64，普通CP。RF频段/Case A～E时间表、SSB raster与MIB字段语义由上层负责；测试中的时序/24位payload是编码核输入，不能当可入网MIB参数集。

## 真实MATLAB独立验证

实际MATLAB 24.1.0.2537033 (R2024a)、5G Toolbox24.1运行[导出脚本](../../examples/ssb/export_NRSSB_reference.m)，调用nrBCH、nrPSS、nrSSS、nrPBCH、nrPBCHDMRS及原生索引/OFDM，Windowing=0。没有使用Python输出冒充MATLAB参考。

25例：Lmax4/8/64、半帧0/1、SFN低位0/2/4/6（覆盖4个载荷Gold分段）、PCI0/1/2/1007（覆盖全部NID2与PCI模4）、k_ssb测试MSB和Lmax64高索引63；普通24RB/FFT512，FR1 SCS30及FR2 SCS120。第25例额外使用100MHz/30kHz载波273RB/FFT4096/Fs122.88MS/s；SSB局部起点24、首符号2，自身仍240子载波×4符号。未声称对15/240kHz或所有频段/Case A～E做过MATLAB独立验证。

[实际参考](../../examples/ssb/NRSSB_reference.json)保存完整输入与环境、全部864编码位、完整复网格和时域波形。[比较报告](../../examples/ssb/NRSSB_comparison.json)逐比特核验BCH，逐RE/逐样点核验网格与波形，并将真实MATLAB波形送到Python接收机。接收资源故意将PCI改成错误值、SSB索引和半帧置0；接收端自行恢复正确PCI、索引及BCH半帧/MIB/SFN低位/CRC。

全部25例通过：编码位精确相等；最大网格误差1.5700924586837752e-16、时域误差4.2207643840401616e-17，均低于1e-10归一化复幅度容差。保留输入、实现及比较脚本SHA256。实际RF载频为0的基带参考，不宣称涵盖全硬件射频一致性。

## 接收及链路测试

接收已知时频窗口、按给定同步量反旋/提前补偿；PSS搜索3条，SSS搜索336条确定PCI。DMRS搜索8个i_bar，Lmax4同时判索引/半帧，Lmax8/64判索引低3位；Lmax64高3位由通过CRC的BCH载荷恢复。按3个PBCH符号估计平坦LS信道并MRC，解物理/载荷两层加扰和Polar/CRC。SC不是SCL，检测门限不是CFAR。

新增测试覆盖全部16个SFN低位、Lmax/半帧/追加位、完整SFN拼接、CRC失败、非法资源/形状/值、960RE及零保留、PSS/SSS边界PCI、错误先验、双Rx复增益、25dB SNR噪声、731Hz频偏/0.23rad初相、2采样点时延以及24/273RB链路。所有绘图仅显示、不保存。

全仓1276项测试通过，3798条语句和1108个分支全部覆盖，100.00%；CI新增ssb测量模块，门限保持100%。示例main(log,plot_config=None,n_size_grid=24)可通过NRPlotConfig关闭绘图，100MHz入口复用同一链路。

## 边界

未实现未知时间位置的滑动PSS捕获、盲CFO、跨频段/Case A～E扫描、跨SSB软合并、SCL、多径插值均衡、混合numerology重采样、MIB ASN.1字段组装/语义校验和CORESET0选择。n_frame/n_slot、MIB的SFN/半帧及显式时频位置的网络语义一致性由调用者保证；不将测试载荷称为可入网配置。强频选信道/大残余同步误差不保证当前平坦模型的检测和CRC性能。

此前10类信道的100MHz用例已在提交afd8f8e中保存；本轮SSB新增工作尚未提交或推送。
