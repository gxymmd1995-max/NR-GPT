# NRPRACH：R15显式时机的PRACH资源与前导

[源码](NRPRACH.py)。以NRCell提供上行BWP、采样率、天线信息；生成TS38.211 V15.2.0 §6.3.3.1的839/139点Zadoff–Chu前导，按§6.3.3.2及§5.3.2映射频率和独立PRACH时序。支持非受限集合的64个前导、13种格式、循环移位与跨根分配。PRACH端口为4000，单个发送波形；多Rx由外部信道生成。

本类描述**一个调用方已调度的发送时机**，不自动解析ConfigurationIndex、帧周期、TDD有效符号、SSB关联、msg1-FDM或功率控制。指定格式B2/B3表示调用方已从混合A/B时机中选中B格式。收到的前导编号不是C-RNTI，也不标识已接入UE；同一时机相同前导碰撞无法区分用户。

## 配置字段

配置冻结；构造/`__post_init__`检查类型、R15组合、BWP边界、FFT/CP整数采样可表示性。调用方负责判断这个时机是否允许发送。

| 字段、默认值 | 含义、范围、单位与示例 |
|---|---|
| cell | NRCell；例NRCell(n_size_grid=52,subcarrier_spacing_khz=30,n_rx_antennas=2)；含采样率和BWP |
| preamble_format='A1' | 字符串0/1/2/3/A1/A2/A3/B1/B2/B3/B4/C0/C2；长格式例'0' |
| subcarrier_spacing_khz=15 | PRACH SCS，kHz；格式0～2固定1.25，3固定5，短格式15/30/60/120；不继承cell的SCS |
| root_sequence_index=0 | 配置逻辑根起点；长0..837、短0..137，整数；例137用于检验短根回绕 |
| zero_correlation_zone=8 | NCS表索引0..15；默认短NCS=15点，非NCS本身；例0表示每根只取一个前导 |
| frequency_start=0 | 首个频域时机相对BWP PRB0的RB偏移，非负整数；例1 |
| frequency_index=0 | 当前频域时机序号0..7；例1偏移一个PRACH占用带宽；必须与frequency_start一起装入BWP，未验证msg1-FDM许可 |
| occasion_start_samples=0 | CP首点在输出捕获数组中的索引，非负整数采样点；例1000；不是slot内符号号 |
| guard_samples=0 | 活动前导后追加静默采样点数，非负整数；例32为信道延迟留尾部空间；不自动套用配置表的RO保护间隔 |
| time_origin_samples=0 | 捕获数组首点的物理时间位置，非负整数采样点，用于半毫秒CP边界；例Fs/8000表示125微秒，**不在波形前插零** |
| restricted_set='unrestricted' | 仅该字符串有效；受限集合Type A/B显式拒绝，不以非受限算法代替 |

`time_origin_samples + occasion_start_samples`共同给出CP开始的时间。time_origin_samples只影响CP边界计数，外部CFO初相由调用方按捕获窗口提供。cell.n_frame/n_slot不是PRACH调度输入，本类不从其隐式计算时机。

## 固定协议表

以下为TS38.211 **V15.2.0原表6.3.3.1-1/-2**的参数转写。CP列是以Ts为单位的基值；短格式须乘15/SCS_RA，Ts=64Tc，CP扩展另按§5.3.2。不是实际采样点数。

| 格式 | L_RA | 有效周期重复数R | CP基值/Ts | PRACH SCS/kHz |
|---|---|---|---|---|
| 0 | 839 | 1 | 3168 | 1.25 |
| 1 | 839 | 2 | 21024 | 1.25 |
| 2 | 839 | 4 | 4688 | 1.25 |
| 3 | 839 | 4 | 3168 | 5 |
| A1/A2/A3 | 139 | 2/4/6 | 288/576/864 | 15/30/60/120 |
| B1/B2/B3/B4 | 139 | 2/4/6/12 | 216/360/504/936 | 15/30/60/120 |
| C0/C2 | 139 | 1/4 | 1240/2048 | 15/30/60/120 |

`_tables.py`的NCS按同版本原表6.3.3.1-5/-6/-7非受限列，索引0..15。长根表`_root_table.json`逐项来自原表6.3.3.1-3（PDF第38页，838项排列）；短根公式按原表6.3.3.1-4交替为1,138,2,137,…,69,70。未采用R16新增L_RA=571/1151或更高SCS。

以下来自同版本**原表6.3.3.2-1**，值为(占用上行RB数,k_bar)；空白组合拒绝。SCS均kHz。

| RA SCS | UL15 | UL30 | UL60 | UL120 |
|---|---|---|---|---|
| 1.25 | (6,7) | (3,1) | (2,133) | — |
| 5 | (24,12) | (12,10) | (6,7) | — |
| 15 | (12,2) | (6,2) | (3,2) | — |
| 30 | (24,2) | (12,2) | (6,2) | — |
| 60 | — | — | (12,2) | (6,2) |
| 120 | — | — | (24,2) | (12,2) |

## 生成公式与变量

下列PRACH-1/2/3均为**本文自编号**，不是原文式号。PRACH-1依据固定TS38.211 V15.2.0 §6.3.3.1及根/NCS原表：

$$
M=\begin{cases}\lfloor L/N_{CS}\rfloor&N_{CS}>0\\1&N_{CS}=0\end{cases},\quad
j=(i_0+\lfloor a/M\rfloor)\bmod(L-1),\quad C=(a\bmod M)N_{CS},
$$

$$
x_{u,C}[n]=\exp\!\left(-j_{\rm im}\pi u\frac{q(q+1)}L\right),\quad q=(n+C)\bmod L,\quad
Y[k]=\sum_{n=0}^{L-1}x_{u,C}[n]e^{-j_{\rm im}2\pi kn/L}.\tag{PRACH-1}
$$

| 变量 | 含义、范围、单位、维度 |
|---|---|
| L、N_CS、M | ZC长度839/139、循环移位间隔0..L-1（表选值）、每根前导数正整数，点数/点数/个数 |
| i_0、a、j | 配置逻辑根0..L-2、前导号0..63、实际逻辑根0..L-2；整数标量 |
| u、C | 原表对应物理根1..L-1、循环移位0..L-1；整数；C正值为序列提前 |
| n、q、k | ZC/移位后/DFT索引，0..L-1；整数；j_im为虚数单位，非逻辑根j |
| x、Y | complex[L]，x单位模、Y模长sqrt(L)；归一化幅度；DFT不含1/sqrt(L) |

数值实现先将整数相位u*q*(q+1)模2L，避免大角度浮点损失。64个前导先增加循环移位，再递增逻辑根；逻辑根按L-1回绕，不能把u直接加1。

PRACH-2依据同版本§5.3.2/§6.3.3.2，限定单numerology的NRCell，k0_mu=0：

$$
N=F_s/\Delta f_{RA},\quad K=\Delta f_{UL}/\Delta f_{RA},\quad
b=N_{BWP}^{start}-N_{grid}^{start}+n_{start}+n_{RA}N_{RB}^{RA},
$$

$$
f_k=(12b-6N_{grid}^{size})K+\bar k+k,\quad
S[f_k\bmod N]=Y[k],\quad
z[n]=\sqrt{K/L}\,\operatorname{IFFT}_N(S)[n].\tag{PRACH-2}
$$

| 变量 | 含义、范围、单位、维度 |
|---|---|
| Fs、Delta_f_RA/UL、K | 小区采样率Hz、RA/UL子载波间隔Hz、其比值无量纲正数 |
| N、b、f_k | PRACH FFT长度正整数、载波局部起始RB、以载波中心为0的整数PRACH频率bin；scalar/scalar/int[L] |
| N_BWP_start、N_grid_start/size | CRB坐标起点及载波RB数，继承cell；RB单位整数 |
| n_start、n_RA、N_RB_RA、k_bar | 配置偏移RB、频域时机号、原表占用RB、原表频率偏移bin；均整数 |
| S、z、n | FFT序频谱complex[N]、一周期时域complex[N]、采样点索引0..N-1 |

IFFT使用NumPy的1/N归一化。sqrt(K/L)是本平台为与MATLAB nrPRACHOFDMModulate幅度一致采用的**工程归一化约定**，不冒充规范强制幅度；额外发送beta再线性缩放，无绝对瓦特/dBm标定。PRACH长格式的N可为12/24倍cell.n_fft，不强制为2的幂。频谱必须用PRACH自己的间隔，不能直接塞入普通NRGrid后调用NROFDM。

PRACH-3依据同版本§5.3.2，短格式CP增加跨半毫秒边界的16Ts：

$$
H=F_s/2000,\quad s=t_0+s_{RO},\quad
B=\left\lfloor\frac{s+C_0+RN-1}{H}\right\rfloor-\left\lfloor\frac{s-1}{H}\right\rfloor,\quad
C_{CP}=C_0+B\frac{1024}{T_{c/sample}}.\tag{PRACH-3}
$$

| 变量 | 含义、范围、单位、维度 |
|---|---|
| H、s、t0、s_RO | 半毫秒样点数、实际CP起点、时间原点、捕获数组中的RO起点；非负整数样点（H正） |
| C0 | 原表CP换算到当前Fs后的基值，正整数样点 |
| R、N、B | 有效周期数1/2/4/6/12、PRACH FFT点数、区间[s,s+C0+RN)内半毫秒边界数；整数 |
| C_CP、Tc/sample | 扩展后CP样点数、每采样点Tc数，正整数；1024Tc=16Ts |

长前导不应用此扩展。C2的CP可能大于一个周期，必须按周期循环取前缀。MATLAB会把C2的一个完整CP周期表示成额外网格符号；对齐验证比较完整CP+活动波形，不能只比较两个实现的CP字段。

## 属性与方法

| 接口 | 返回、用途和示例 |
|---|---|
| sequence_length、repetitions、n_cs | L、R、NCS整数标量；默认139、2、15 |
| n_prbs、k_bar | 固定组合原表值；默认RA15/UL30为6、2 |
| n_fft、base_cp_tc、cp_samples | PRACH FFT点数、CP基值Tc数、实际CP采样点；默认52RB/UL30时2048、18432、304 |
| active_samples、waveform_samples | CP+R*N，以及前导前偏移+活动+guard的总长度；整数采样点 |
| frequency_bins | 以载波中心为0的int[L]频率bin，可为负；默认第0点为-622 |
| preamble_parameters(a) | (实际逻辑根,u,C)；默认a=1返回(0,1,15) |
| sequence(a) | complex[L]移位ZC；例sequence(1)，单位模 |
| generate(a) | complex[L]未归一化DFT；例generate(1) |
| spectrum(a) | complex[N] FFT顺序，未占用bin为0；例spectrum(1) |
| useful_waveform(a) | complex[N]一有效周期；例useful_waveform(1)，未乘beta |

```python
from cell import NRCell
from prach import NRPRACH
r = NRPRACH(NRCell(n_size_grid=52,subcarrier_spacing_khz=30),
            preamble_format='A1',subcarrier_spacing_khz=15,
            zero_correlation_zone=8,guard_samples=32)
assert r.preamble_parameters(1) == (0,1,15)
assert r.n_fft == 2048 and r.cp_samples == 304
```

```mermaid
flowchart LR
    A[前导号和逻辑根] --> B[物理ZC根与循环移位]
    B --> C[ZC序列DFT]
    C --> D[独立PRACH频谱]
    D --> E[IFFT和周期重复]
    E --> F[CP和时机偏移]
    F --> G[时域信道与Rx]
    G --> H[相关检测和采样点时延]
```

边界：非受限集合、整数采样、单小区单numerology、显式时机。无受限集合、多numerology k0偏移、完整ConfigurationIndex调度、RAR/Msg3、接入冲突解决、自动频偏搜索或PRACH功率爬坡。参见[MATLAB验证](../../documentation/validation/NRPRACH_validation.md)。
