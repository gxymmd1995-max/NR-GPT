# 全仓语句与分支覆盖率补齐

本轮对1045项测试、97.29%综合覆盖率的状态补齐有效异常与边界测试；最终在Python 3.14.0下1101项全部通过；3286条语句、982个分支全部覆盖，缺失语句0、部分分支0，综合覆盖率100.00%，61个测量文件均达到100%。

## 改动与依据

- 将紧凑的单行函数、条件及循环展开为多行，保持计算和协议参数不变。原先未执行的raise与已执行的if位于同一行，语句统计不能充分暴露它们；展开后逐一验证两条路径，而非将缺失一概归因于工具。
- 补Polar/RM/LDPC/UCI/UL-SCH的非法配置、输入形状/类型/值及非有限LLR；LDPC错误校验方程和Polar可靠度表损坏使用局部monkeypatch故障注入，验证明确报错，不伪造MATLAB结果。
- 补PUCCH F1～F4的资源/网格/波形校验、码率超限、F3序列跳变、F4扩频/解扩输入以及调用方共享绘图器路径；关闭绘图的共享器仍执行真实收发链路。
- 补PDSCH/PUSCH短Type-A分配的附加DMRS回退；PDSCH非法cell和不完整双符号DMRS。
- PRACH的FFT及CP整数性由合法NRCell和固定R15频率表保证，删除重复的不可达检查，保留参数表组合、频率边界及采样生成测试。
- DL-SCH单码块BG/Z满足2Z<B，Ncb>=1的循环缓冲含非填充索引0；删除不可达空选择检查。以全部字节对齐TBS、BG选择码率区域验证约束，并针对8种TBS、4个RV检查Nref=1输出；多码块仍明确拒绝。

不使用pragma no cover、omit或exclude_lines，不缩减原有覆盖率测量模块。测试中故障注入仅用于校验损坏数据时的错误行为，正常链路仍与真实MATLAB向量独立比较。

## 验证入口

```powershell
.venv\Scripts\python -X utf8 -m pytest --require-matlab --cov=cell --cov=grid --cov=diagnostics --cov=srs --cov=common --cov=channel --cov=pucch --cov=pusch --cov=pdsch --cov=prach --cov-branch --cov-fail-under=100 --cov-report=term-missing:skip-covered -q
```

对受改动源码SHA影响的12份独立比较报告实际重新运行比较脚本，均通过并重新生成哈希；MATLAB参考向量保持原始实测数据。CI全仓门限提高为100%，保留原基础模块100%复查。

另对15个仅做多行展开的已有源码文件核对AST，均与Git原版等价。MATLAB比对后的源码哈希一致性检查通过。

本轮不创建Git提交或推送。
