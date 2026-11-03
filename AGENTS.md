# 项目开发约定

- `documentation/protocols/` 仅存放协议原文及协议译文，不放开发计划、类说明、测试报告。不再使用根目录 `docs/`。
- 总体设计放 `documentation/`；类源码直接按模块放在 `src/<模块>/`，不增加 `nrphy` 包装层。
- 每个类必须有单元测试；独立 Markdown 类文档与对应源码放在同一目录，如 `src/cell/NRCell.md`。
- 类文件和类文档使用准确类名（`NRCell.py` / `NRCell.md`）；相关示例、测试、MATLAB 脚本和产物统一保留 `NRCell` 大小写，如 `NRCell_demo.py`、`test_NRCell.py`、`export_NRCell_reference.m`、`NRCell_reference.json`。模块目录使用小写，变量及方法使用 snake_case。
- 示例目录与源码模块对应，如 `examples/cell/`；该模块示例生成的中间文件、MATLAB 参考 JSON、图片均保存在对应示例目录中。
- 安装生成的 `*.egg-info/` 是可删除的元数据，不是源码，不提交 Git。
- 类文档须解释用途、边界、每个字段/属性/方法，并提供可运行示例；适合时附图。
- 协议参数表必须注明规范编号、版本、原文章节和原表号；派生表注明推导依据。
- 公式必须标注规范版本与章节。自定义公式编号必须明确为文档自编号，不冒充原文编号。
- 仅使用固定的 R15 基线；不从现有 R18 文档静默引入功能。
- 实现具体物理信道/信号必须与 MATLAB 5G Toolbox 独立比对，保留输入、生成脚本、MATLAB/Toolbox 版本、向量和比较结果。
- 没有 MATLAB 实测向量时，明确标记未验证，不得伪造或用 Python 输出充当 MATLAB 结果。
- 每次功能提交运行相关单元测试及独立参考测试，代码注释须说明单位、坐标和算法依据。
- Git 提交不得包含虚拟环境、访问令牌、私钥或运行缓存；保留远端已有历史。
- 项目原创代码采用根目录 LICENSE 中的个人非商业免费、商业付费授权条款，不得将其描述为 Apache/MIT 或无条件商业可用的开源项目；第三方协议资料保留原有许可。
- 在用户明确通知前，不创建 Git 提交、不推送。

## 目录结构与查阅入口

以下为当前目录结构；新增或移动模块时同步维护本节。先按目录定位，不为确认已列出的结构而重复扫描全仓库。树中的 `<类名>` 是命名模板，不表示该目录下每个类都有独立的导出/比较脚本。

```text
NR1024/
├── AGENTS.md                       # 开发约定与文件定位入口
├── README.md                       # 使用方式、功能概览、文档入口
├── pyproject.toml                  # 安装依赖、包发现和测试配置
├── LICENSE                         # 个人非商业免费、商业付费条款
├── .github/workflows/tests.yml     # CI测试配置
├── src/                            # 类源码及对应类文档，同目录同名
│   ├── cell/                       # NRCell.py/.md：小区、网格尺寸、FFT、CP时序
│   ├── grid/                       # NRGrid.py/.md；channel_colors.py/.md
│   ├── common/                     # NRCommon、NROFDM、NRPhaseRotation、NRUplinkCodebook、NRUCICode及编解码类
│   │                               # _validation.py：校验；_uplink_tables.py：码本；_low_papr_tables.py：共享12点相位表
│   ├── channel/                    # NRChannel.py/.md：样点TA、CFO、按SNR加噪
│   ├── pucch/                      # NRPUCCH0/1/2/3/4资源、Transmitter、Receiver及同级文档
│   ├── srs/                        # NRSRS.py/.md、NRSRSReceiver.py/.md
│   │                               # _tables.py：SRS协议参数表
│   └── diagnostics/                # ExampleLogger、NRPlotConfig、NRStagePlotter及同级文档
├── examples/                       # 示例、MATLAB参考及产物；按源码模块对应
│   ├── cell/
│   ├── grid/
│   ├── common/
│   ├── channel/
│   ├── pucch/
│   └── srs/
│       # 各目录README.md：脚本和产物索引
│       # <类名>_demo.py、plot_*.py：运行与绘图示例
│       # export_<类名>_reference.m：真实MATLAB参考生成入口
│       # compare_<类名>_reference.py：已有的独立比较入口
│       # *_reference.json：参考向量；*_comparison.json：比较摘要
│       # *_summary.json、*.npz、*.csv、*.png、*.svg：生成数据与图像
│       # *.log：本地运行日志，不提交；diagnostics通过各模块示例使用
├── tests/                          # 测试文件按类名平铺，不按源码模块再分目录
│   ├── unit/test_<类名>.py          # 单元测试，另含颜色等辅助功能测试
│   ├── matlab/test_<类名>_matlab.py  # 独立MATLAB参考比较
│   ├── integration/                # test_SRS_waveform_chain.py、test_PUCCH0_waveform_chain.py
│   └── conftest.py                 # 测试选项与公共配置
└── documentation/
    ├── architecture.md             # 总体设计、边界与坐标约定
    ├── feature_matrix.md           # 已实现/未实现能力
    ├── formula_reference.md        # 公式变量含义、范围、单位与维度
    ├── spec_manifest.md            # 固定协议版本、文件清单、SHA256和章节追溯
    ├── planning/                   # 开发计划
    ├── validation/                 # 各模块验证报告；project_audit.md为历史审计
    └── protocols/                  # 仅协议PDF原文和辅助译文，大文件按章节查阅
```

| 本次任务 | 优先查阅 | 何时扩展读取 |
|---|---|---|
| 修改某个类 | `src/<模块>/<类名>.py`相关方法、同目录类文档相关节、`tests/unit/test_<类名>.py`对应测试 | 确认涉及依赖后再读其被调用接口；不顺带通读其他模块 |
| 补公式说明/解释变量 | 对应类文档、`documentation/formula_reference.md`相关节 | 核验标准定义时通过`spec_manifest.md`定位固定版本协议章节 |
| 核对协议公式/原表 | `documentation/spec_manifest.md`、`documentation/protocols/`指定章节 | 相邻定义、引用原表或有歧义时再扩展；不默认读完整规范 |
| 运行/修改示例 | `examples/<模块>/README.md`、指定示例脚本 | 按实际调用定位源码；只有分析结果时才读该示例产物 |
| 检查MATLAB一致性 | `tests/matlab/`对应测试、验证报告、已有`*_comparison.json`必要字段 | 追查某案例时再解析`*_reference.json`指定case和生成脚本；相位参考通常并入NROFDM |
| 排查测试失败 | 失败用例、异常位置、对应实现 | 由失败证据逐步扩展；不先读取全部测试和源码 |
| 调整依赖/CI/安装 | `pyproject.toml`、`.github/workflows/tests.yml` | 仅在发现导入/包发现问题时查对应`__init__.py`或目录 |
| 查询进度/实现边界 | `documentation/feature_matrix.md`、相关类文档 | 需要历史原因才读`planning/`、`validation/project_audit.md` |

## 避免无效读取与 Token 浪费

- **读取必须服务于一个具体问题**：调用前明确“要确认什么、从哪个文件/字段获得、什么结果足以停止”。不要出于“先熟悉一下项目”而通读README、全部源码、全部文档或历史报告。
- **按上表确定最小范围**：定位实现不需要同时读取示例结果；解释字段不需要加载参考向量；仅修改文档不需要遍历算法实现。需要核实文档与代码一致时，定向读取对应方法或常量即可。

- 先明确本次需要回答的问题，再定位文件。已知路径直接访问；未知路径先用 `rg --files` 配合目录/文件名过滤，再在相关文件内搜索符号或章节。不要默认全仓库递归读取。
- 搜索优先缩小目录和文件类型；只需路径时用 `rg -l`，只需存在性时用 `rg -q`，需要内容时用 `rg -n` 并限制上下文。默认排除 `.git/`、`.venv/`、缓存、`*.egg-info/`、日志、生成产物和大型参考向量；任务确实涉及它们时再定向访问。
- 普通文本先按函数、标题或命中行读取，仅包含理解问题所需的上下文。小文件且整体相关时可全文读取；不要机械按固定行数把大文件分批读完，也不要为了少读几行而遗漏必要定义。
- 同一任务已读取且未改变的内容不重复读取。沿用已确认的结论、路径和行号；文件发生变化、上下文缺失或需要核验时，仅重读相关范围。上下文压缩后优先使用摘要，不从头遍历项目。
- 协议文档先用规范清单确定版本，再定位原文章节、公式、表号及相邻定义。不要默认读取整份译文或提取整份PDF；仅在需要跨章节核对时扩展范围。保持必要的规范核验，不以节省Token为由猜测参数或省略验证。
- 大型JSON先在脚本内部解析，仅输出所需字段、键名、形状、案例数量、误差统计或少量样例。NPZ/CSV同样先读元数据或指定列/行；不要将完整参考向量、波形、资源网格或大型summary输出到对话。
- 日志即使只取最后几行，也可能包含超长单行或完整数组。读取日志时同时限制行数和每行字符数；默认只提取状态、异常、失败案例及关键指标。不得直接全量输出示例调用日志、压缩数据、base64图片或二进制文件。
- 每次工具调用设置与任务相称的输出上限。对可能超长的内容，先在脚本内部截取/汇总再输出；工具的 `max_output_tokens` 仅作兜底。出现截断时改用更精确的过滤条件，不反复重发同一大段输出。
- 检查改动先看 `git status --short`、`git diff --stat`，再定向查看相关文件的diff。首次读取未跟踪文件同样遵守范围限制；不要为了审查少量改动而重读全部源码、文档或产物。
- 独立搜索可合并调用并分别限定输出；有依赖的读取按结果逐步展开。相同状态不重复查询，无新变化不重复运行已通过的检查。新增改动或发现问题后，按影响范围补做必要验证。
- 耗时脚本将详细结果保存在项目约定位置，对话只返回摘要和文件路径。任务结束或需要压缩上下文时，记录已完成工作、关键结论、待办与必要文件位置，避免下一轮重新扫描。

PUCCH F1定位：`src/pucch/NRPUCCH1.py/.md`、`NRPUCCH1Transmitter.py/.md`、`NRPUCCH1Receiver.py/.md`；示例与MATLAB参考在`examples/pucch/`，类单测在`tests/unit/test_NRPUCCH1*.py`，MATLAB入口为`tests/matlab/test_NRPUCCH1_matlab.py`。

PUCCH F2定位：`src/pucch/NRPUCCH2.py/.md`、`NRPUCCH2Transmitter.py/.md`、`NRPUCCH2Receiver.py/.md`；共享小块码`src/common/NRSmallBlockCode.py/.md`及原表`_small_block_tables.py`。示例和真实MATLAB向量在`examples/pucch/`；按类名查`tests/unit/`和`tests/matlab/test_NRPUCCH2_matlab.py`。

信道编码入口：src/common/NRPolarCode、NRLDPCCode、NRRMCode及各自.md；固定R15表_coding_tables.json；tests/unit/test_同类名.py；examples/common/export_NRChannelCodes_reference.m与compare_NRChannelCodes_reference.py；tests/matlab/test_NRChannelCodes_matlab.py。

完整UCI/F3定位：src/common/NRUCICode.py/.md；src/pucch/NRPUCCH3.py/.md及对应Transmitter/Receiver。F2长UCI示例NRPUCCH2_Polar_demo.py，F3示例NRPUCCH3_demo.py；实际MATLAB参考在examples/common/NRUCICode_*及examples/pucch/NRPUCCH3_*；最新验证documentation/validation/NRPUCCH3_validation.md。

F4定位：src/pucch/NRPUCCH4.py/.md及对应Transmitter/Receiver；examples/pucch/NRPUCCH4_demo.py、export_NRPUCCH4_reference.m、compare_NRPUCCH4_reference.py；tests/unit/test_NRPUCCH4*.py、tests/matlab/test_NRPUCCH4_matlab.py；验证documentation/validation/NRPUCCH4_validation.md。
