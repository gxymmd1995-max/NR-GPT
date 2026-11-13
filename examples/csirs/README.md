# csirs参考信号示例

- [NRCSIRS_demo.py](NRCSIRS_demo.py)：直接运行显示资源网格和接收测量；run_case(False)关闭绘图；[类文档](../../src/csirs/NRCSIRS.md)。

- [100 MHz / 30 kHz示例](NRCSIRS_100MHz_30kHz_demo.py)：273 RB载波、272 RB参考资源、双Rx经AWGN后的信道测量。

实际MATLAB导出：[统一脚本](../common/export_NRReferenceSignals_reference.m)；[输入及向量](../common/NRReferenceSignals_reference.json)；[比较](../common/compare_NRReferenceSignals_reference.py)；[结果](../common/NRReferenceSignals_comparison.json)。这是共享参考文件，不是Python自生成的MATLAB结果。
