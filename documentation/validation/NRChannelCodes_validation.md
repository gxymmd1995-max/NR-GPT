# Common信道编码核验证

固定TS38.212 V15.2.0 §5.3.1、§5.3.2，Polar可靠度及输入交织表、LDPC BG1/BG2及lifting集合直接从原文提取。经典RM不是该标准小块码，二者明确分离。

实际MATLAB R2024a 24.1.0.2537033、5G Toolbox24.1：examples/common/export_NRChannelCodes_reference.m导出5个Polar母码向量N64/128/256/512/1024、K=N/2；6个LDPC向量BG1/BG2、Z2/8/16；另3个经典RM r0/1/2,m4由独立原生MATLAB多项式求值生成，未声称Toolbox提供经典RM函数。compare_NRChannelCodes_reference.py将14个实际码字逐位比较，并以它们构造正负20的软输入进行Python译码，编码/译码差异均0。环境、输入、完整码字及SHA256保存在参考/比较JSON中。

单测覆盖Polar N32～1024及输入交织开关；LDPC两基图的8个lifting集合代表及额外Z16，独立检查完整H校验综合及译码；经典RM多数逻辑纠正至设计纠错半径。36项单元测试及1个MATLAB入口通过。MATLAB对比为无噪声，不构成BLER性能或SCL等价性声明。非零PC、速率匹配打孔/缩短、CRC、信道自动参数选择尚未实现；LDPC任意filler/大Z性能及Polar输入交织尚无独立MATLAB实测，文档仅标单测覆盖。

接口边界：Polar类是指定N、零PC位母码与SC；LDPC类输入已分段且已选择Z的单码块，输出按规范先打孔2Z（不包含后续速率匹配）；经典RM类是通用多项式求值/硬多数译码。未解除现有PUCCH F2的12位以上限制。无Git提交或推送。

当前更新：NRPolarCode母码接口不变，完整UCI的CRC/PC/速率匹配/分段在NRUCICode实现并已接通F2/F3；旧段落“尚未解除F2限制”为历史状态。当前见[新报告](NRPUCCH3_validation.md)。
