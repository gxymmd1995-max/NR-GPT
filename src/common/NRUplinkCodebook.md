# NRUplinkCodebook：上行 RI/TPMI 码本搜索

[NRUplinkCodebook.py](NRUplinkCodebook.py)提供R15 PUSCH标准码本矩阵及基于信道估计的RI/TPMI搜索，导入方式 `from common import NRUplinkCodebook`。没有实例状态，使用静态方法。SRS接收机通过这个类推荐后续上行发送的层数RI和矩阵编号TPMI；这些建议还需调度器依据UE能力、配置及DCI规则采用。

固定 **TS38.211 V15.2.0 §6.3.1.5**，只支持1/2/4端口、关闭变换预编码。尚未实现完整PUSCH调制链。矩阵是规范定义；互信息评分、等总功率比较、平分规则、噪声下限是项目接收机策略，不冒充标准规定的唯一RI/TPMI选择算法。

## 原表与矩阵坐标

以下为原表追溯清单，不是新的码本定义。数据存于 [_uplink_tables.py](_uplink_tables.py)，按 `(n_ports,rank)` 索引，每条为 `(分母平方,未缩放复整数矩阵)`。

| 端口数 | RI/层数 | TPMI范围 | TS38.211 V15.2.0原文 |
|---|---|---|---|
| 1 | 1 | 0 | §6.3.1.5正文W=1 |
| 2 | 1 | 0..5 | 表6.3.1.5-1 |
| 2 | 2 | 0..2 | 表6.3.1.5-4 |
| 4 | 1 | 0..27 | 表6.3.1.5-3，关闭变换预编码 |
| 4 | 2 | 0..21 | 表6.3.1.5-5 |
| 4 | 3 | 0..6 | 原表题印作6.3.1.5.4-6，对应本节三层码本 |
| 4 | 4 | 0..4 | 表6.3.1.5-7 |

共72个矩阵。矩阵转录自项目R15辅助译文的原文矩阵栏，并与真实MATLAB全部72个结果独立比对，没有用MATLAB输出生成Python表。Python矩阵为 `[发送端口,层]`；MATLAB nrPUSCHCodebook返回 `[层,发送端口]`，独立脚本使用**非共轭转置**恢复同一坐标。[MathWorks接口说明](https://www.mathworks.com/help/5g/ref/nrpuschcodebook.html)也说明其输出是规范矩阵的转置；该页含后续版本功能，本类不采用8端口或其他新增码本。

## 常量与接口

`NOISE_FLOOR=1e-12`：归一化复噪声功率/RE的数值下限，避免零噪声导致除零；工程常量，不是协议值。不保存实例字段/属性。

`matrix(n_ports,rank,tpmi)` 返回新complex128矩阵副本，保持原表系数：

| 参数 | 含义/示例 |
|---|---|
| n_ports | Python int，1/2/4；例如`matrix(2,1,4)` |
| rank | Python int，1..n_ports，输出列数 |
| tpmi | Python int，对应上表范围；2端口/1层/4得到`[1,j]^T/sqrt(2)` |

整数类型拒绝bool/float/NumPy int，类型错误TypeError，非法范围/组合ValueError。修改返回矩阵不改变下一次返回值。

`select(channel,noise_power,tx_power=1.0,max_rank=None,allowed_tpmi=None)`：

| 参数 | 含义、单位、示例 |
|---|---|
| channel | 非空有限复数 `[频点,Rx,Tx]`，Tx=1/2/4；频点应来自当前用户已探测频段，不把未测频段无条件计入 |
| noise_power | 非负有限实数，每接收分支平均复噪声功率/RE，例如0.001；使用max(noise,NOISE_FLOOR) |
| tx_power | 非负有限实数，UE归一化总发送功率，默认1；不是dBm；0不生成有效建议 |
| max_rank | None默认min(Rx,Tx)；也可传1..Tx的Python int，再取Rx上限；例如2 |
| allowed_tpmi | None搜索全码本；或`{1:[2,4],2:[0]}`只搜索给定候选，列表不可空/重复，rank须不超过有效上限；由调用者实现UE能力/配置约束 |

错误的H/功率范围/候选集合报ValueError，错误实数类型报TypeError。返回字典：

| 字段 | 作用 |
|---|---|
| ri / tpmi | 最佳层数/矩阵号；零信道或tx_power=0时为None，非实际DCI消息 |
| precoder | 最佳**原表**W；无建议为None，仍需发送侧按功率约定应用 |
| score_bps_hz | 平均高斯互信息代理值，单位bit/s/Hz，不是MCS吞吐量或编码链实测速率 |
| candidates | 每候选`ri,tpmi,score_bps_hz`，按rank/TPMI升序 |
| scoring_normalization | 明确评分使用`W/FrobeniusNorm(W)`保持相同UE总功率 |
| noise_power_used | 应用数值下限后的功率 |

## 评分公式

以下U1/U2为本文自编号。W来自上述R15原表，评分是项目算法。以等UE总功率比较时，令：

$$
\widetilde W=W/\|W\|_F,\quad G_k=H_k\widetilde W,\quad
\rho=P_{UE}/\max(\sigma^2,10^{-12}).\tag{U1}
$$

$$
J(r,t)=\frac1F\sum_k\sum_i\log_2(1+\rho\max(\lambda_i(G_k^HG_k),0)).\tag{U2}
$$

搜索最大J；差异不超过1e-10时保持较低RI/TPMI。评分时的归一化与`matrix`返回的标准矩阵分开，不能把原表中部分端口激活时较小的范数误当成矩阵转录错误。默认假设接收噪声白化/各Rx使用相同标量噪声；没有接入完整空间干扰协方差或MU-PUSCH干扰/调度模型。

```python
import numpy as np
from common import NRUplinkCodebook

w = NRUplinkCodebook.matrix(2, 1, 4)
assert w.shape == (2, 1)
result = NRUplinkCodebook.select(np.eye(4)[None,:,:], noise_power=0.001)
assert result["ri"] == 4 and result["tpmi"] == 0
limited = NRUplinkCodebook.select(np.eye(4)[None,:,:], 0.01,
    max_rank=2, allowed_tpmi={1:[0], 2:[1,3]})
assert limited["ri"] <= 2
```

单元测试为 [test_NRUplinkCodebook.py](../../tests/unit/test_NRUplinkCodebook.py)。真实独立脚本 [export_NRUplinkCodebook_reference.m](../../examples/common/export_NRUplinkCodebook_reference.m)使用R2024a 5G Toolbox，72个矩阵逐元素误差容限1e-15；接收机24组实测还独立验证RI/TPMI选择，见 [接收验证报告](../../documentation/validation/NRSRSReceiver_validation.md)。
