# NRCommon 序列示例

```powershell
.venv\Scripts\python -X utf8 examples/common/NRCommon_demo.py
.venv\Scripts\python -X utf8 -m pytest tests/unit/test_NRCommon.py tests/matlab/test_NRCommon_matlab.py --require-matlab
```

静态类的完整变量/函数、种子bit顺序和公式出处见 [NRCommon.md](../../src/common/NRCommon.md)。所有产物与脚本同目录。

| 文件 | 用途（项目说明表） |
|---|---|
| [NRCommon_demo.py](NRCommon_demo.py) | main(log)演示Gold 128bit、30kHz一帧内SRS u/v，写JSON和图片；调用链日志和序列内容输出到同级log |
| [NRCommon_sequences.json](NRCommon_sequences.json) | c_init/gold_length/gold_offset/gold_bits；cell/symbol_start/n_symbols/sequence_length；frame_symbol_indices/group_hopping_u/sequence_hopping_v，后两者来自两个互斥的配置 |
| [NRCommon_sequences.png](NRCommon_sequences.png) / [SVG](NRCommon_sequences.svg) | Gold二进制阶梯图和每个SRS符号的u/v散点图，公式出处标在图片中 |
| [export_NRCommon_reference.m](export_NRCommon_reference.m) | outputFile可选，默认同级NRCommon_reference.json；独立使用nrPRBS，不调用Python |
| [NRCommon_reference.json](NRCommon_reference.json) | MATLAB/Toolbox版本、UTC时间、固定基线与20组input/bits；种子0/1/42/1023/2**31-1，长度1/31/128/0，含offset17/1600 |

```powershell
& 'E:\Program Files\MATLAB\R2024a\bin\matlab.exe' -batch "addpath('examples/common'); export_NRCommon_reference;"
```

参考比特必须来自实际MATLAB运行。SRS的u/v继续使用 [NRSRS_reference.json](../srs/NRSRS_reference.json) 中nrSRS返回的SeqGroup/NSeq，避免重构公共层时替换或伪造既有参考。非活跃case的u/v不作为发送参考比较。
