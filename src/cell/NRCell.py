"""不可变 NR 小区配置，基线为 TS 38.211 V15.2.0。

这是链路仿真的单方向、单 numerology、单活动 BWP 配置切片。
不代表完整 gNB，也不检查射频频段、信道带宽或 TDD 时隙格式。
原文表格及公式出处见 src/cell/NRCell.md。
"""

from dataclasses import asdict, dataclass, replace
from itertools import accumulate
from typing import ClassVar


def _integer(name: str, value: int, lower: int, upper: int | None = None) -> None:
    """严格验证 Python 整数及闭区间，不改变 value。

    Args:
        name: 错误信息使用的参数名称。
        value: 待验证值；bool 虽是 int 子类，也必须拒绝。
        lower: 允许的最小值，包含端点。
        upper: 允许的最大值，包含端点；None 表示不设上限。

    Raises:
        TypeError: value 不是 Python int。
        ValueError: value 低于 lower，或在指定 upper 时超出上限。
    """
    if type(value) is not int:
        raise TypeError(f"{name} must be an int (bool is not accepted)")
    if upper is None:
        if value < lower:
            raise ValueError(f"{name} must be >= {lower}, got {value}")
    elif not lower <= value <= upper:
        raise ValueError(f"{name} must be in [{lower}, {upper}], got {value}")


@dataclass(frozen=True, slots=True)
class NRCell:
    """NR 小区的基础参数、时序和资源坐标。

    输入字段使用 Python snake_case；`to_matlab_config` 导出 nrCarrierConfig
    名称。构造后不可修改，通过 dataclasses.replace 或 with_slot_offset
    产生新配置，防止关联的资源网格因外部修改而失效。

    Examples:
        >>> cell = NRCell(n_cell_id=42, n_start_grid=10,
        ...               bwp_start=20, bwp_size=24)
        >>> cell.prb_to_crb(0)
        20
        >>> cell.slots_per_frame
        20
    """

    # PCI，见 TS 38.211 §7.4.2.1；不是 NR Cell Global Identifier。
    n_cell_id: int = 1
    # kHz；仅接受 TS 38.211 V15.2.0 表 4.2-1 的五种 numerology。
    subcarrier_spacing_khz: int = 30
    cyclic_prefix: str = "normal"  # CP 类型；extended 仅配 60 kHz，同表 4.2-1。
    # CRB 坐标中的载波起点与 RB 数，见 §4.4.2。
    n_size_grid: int = 52
    n_start_grid: int = 0
    # 单活动 BWP，起点相对 CRB 0，不是相对载波起点，见 §4.4.4.4/§4.4.5。
    # None 表示采用整个载波；__post_init__ 将其规范化为整数。
    bwp_start: int | None = None
    bwp_size: int | None = None
    # 完整 10 bit SFN，范围 0..1023；TS 38.331 V15.2.1 §6.2.2 MIB。
    n_frame: int = 0
    # 帧内时隙编号，TS 38.211 §4.3.2；不采用 MATLAB 的任意累积计数语义。
    n_slot: int = 0
    # TS 38.211 §4.3.1：模式元数据，不自动推导 TDD 上下行符号分配。
    duplex_mode: str = "TDD"
    # 仿真端点的物理收发分支数，不等同于逻辑天线端口或层数（§4.4.1）。
    n_tx_antennas: int = 1
    n_rx_antennas: int = 1

    SUBCARRIERS_PER_RB: ClassVar[int] = 12  # TS 38.211 §4.4.4.1
    SUBFRAMES_PER_FRAME: ClassVar[int] = 10  # TS 38.211 §4.3.1
    FRAME_DURATION_S: ClassVar[float] = 0.01  # TS 38.211 §4.3.1
    SFN_MODULUS: ClassVar[int] = 1024  # TS 38.331 §6.2.2 MIB (10-bit SFN)
    TC_FREQUENCY_HZ: ClassVar[int] = 1_966_080_000  # 480000 × 4096，§4.1
    TS_FREQUENCY_HZ: ClassVar[int] = 30_720_000  # 15000 × 2048，§4.1
    KAPPA: ClassVar[int] = 64  # Ts/Tc，§4.1
    MIN_FFT_SIZE: ClassVar[int] = 128  # 平台约定：保证普通 CP 采样点为整数

    def __post_init__(self) -> None:
        """校验类型、R15 numerology、帧编号及 BWP 包含关系。"""
        _integer("n_cell_id", self.n_cell_id, 0, 1007)
        _integer("subcarrier_spacing_khz", self.subcarrier_spacing_khz, 15, 240)
        if self.subcarrier_spacing_khz not in (15, 30, 60, 120, 240):
            raise ValueError("R15 subcarrier_spacing_khz must be 15, 30, 60, 120 or 240")
        if not isinstance(self.cyclic_prefix, str):
            raise TypeError("cyclic_prefix must be a str")
        if self.cyclic_prefix not in ("normal", "extended"):
            raise ValueError("cyclic_prefix must be 'normal' or 'extended'")
        if self.cyclic_prefix == "extended" and self.subcarrier_spacing_khz != 60:
            raise ValueError("extended cyclic prefix requires 60 kHz in R15")
        # TS 38.331 V15.2.1 §6.3.2 SCS-SpecificCarrier 的带宽与偏移范围。
        _integer("n_size_grid", self.n_size_grid, 1, 275)
        _integer("n_start_grid", self.n_start_grid, 0, 2199)
        _integer("n_frame", self.n_frame, 0, self.SFN_MODULUS - 1)
        _integer("n_slot", self.n_slot, 0, self.slots_per_frame - 1)
        if not isinstance(self.duplex_mode, str):
            raise TypeError("duplex_mode must be a str")
        if self.duplex_mode not in ("TDD", "FDD"):
            raise ValueError("duplex_mode must be 'TDD' or 'FDD'")
        _integer("n_tx_antennas", self.n_tx_antennas, 1)
        _integer("n_rx_antennas", self.n_rx_antennas, 1)

        # frozen dataclass 初始化时唯一允许的赋值，用于消除可选参数的歧义。
        if self.bwp_start is None:
            object.__setattr__(self, "bwp_start", self.n_start_grid)
        if self.bwp_size is None:
            object.__setattr__(self, "bwp_size", self.n_size_grid)
        # 2473 = 2199 + 275 - 1 为软件输入包络，不是额外的规范 BWP 上限。
        _integer("bwp_start", self.bwp_start, 0, 2473)
        _integer("bwp_size", self.bwp_size, 1, 275)
        # TS 38.211 §4.4.5：BWP 的整个半开区间必须包含在载波内。
        if (self.bwp_start < self.n_start_grid
                or self.bwp_start + self.bwp_size > self.n_start_grid + self.n_size_grid):
            raise ValueError("BWP must be fully contained in the carrier grid")

    @property
    def numerology(self) -> int:
        """参数集 μ；Δf = 15 × 2**μ kHz，TS 38.211 表 4.2-1。"""
        return (self.subcarrier_spacing_khz // 15).bit_length() - 1

    @property
    def symbols_per_slot(self) -> int:
        """每时隙 OFDM 符号数，TS 38.211 表 4.3.2-1/-2。"""
        return 12 if self.cyclic_prefix == "extended" else 14

    @property
    def slots_per_subframe(self) -> int:
        """每 1 ms 子帧的时隙数，TS 38.211 表 4.3.2-1/-2。"""
        return 1 << self.numerology

    @property
    def slots_per_frame(self) -> int:
        """每 10 ms 帧的时隙数，TS 38.211 表 4.3.2-1/-2。"""
        return self.SUBFRAMES_PER_FRAME * self.slots_per_subframe

    @property
    def nominal_slot_duration_s(self) -> float:
        """平均时隙时长；不用于推导精确逐符号采样时刻。

        由 §4.3.1/§4.3.2 推导。实际 CP 与符号边界需按 §5.3.1 计算，
        部分 numerology 的不同 slot 实际时长不完全相同。
        """
        return self.FRAME_DURATION_S / self.slots_per_frame

    @property
    def subframe_index(self) -> int:
        """当前帧内子帧索引 0..9，由 §4.3.2 的编号关系推导。"""
        return self.n_slot // self.slots_per_subframe

    @property
    def slot_in_subframe(self) -> int:
        """当前子帧内时隙索引，由 §4.3.2 的编号关系推导。"""
        return self.n_slot % self.slots_per_subframe

    @property
    def n_subcarriers(self) -> int:
        """载波网格子载波数，TS 38.211 §4.4.2/§4.4.4.1。"""
        return self.n_size_grid * self.SUBCARRIERS_PER_RB

    @property
    def bwp_n_subcarriers(self) -> int:
        """活动 BWP 子载波数，由 §4.4.4.1/§4.4.5 推导。"""
        return self.bwp_size * self.SUBCARRIERS_PER_RB

    @property
    def occupied_bandwidth_hz(self) -> int:
        """网格名义带宽 Nsc·Δf（Hz），由 TS 38.211 §4.2/§4.4.2 推导。

        不等于包含保护带的 RF 信道带宽。
        """
        return self.n_subcarriers * self.subcarrier_spacing_khz * 1000

    @property
    def n_id_1(self) -> int:
        """PCI 组号 0..335，TS 38.211 §7.4.2.1。"""
        return self.n_cell_id // 3

    @property
    def n_id_2(self) -> int:
        """组内 PCI 编号 0..2，TS 38.211 §7.4.2.1。"""
        return self.n_cell_id % 3

    @property
    def subframes_per_frame(self) -> int:
        """系统帧包含的子帧数，固定 10；TS 38.211 §4.3.1。"""
        return self.SUBFRAMES_PER_FRAME

    @property
    def symbols_per_subframe(self) -> int:
        """每子帧 OFDM 符号数，由 §4.3.2 表 4.3.2-1/-2 推导。"""
        return self.slots_per_subframe * self.symbols_per_slot

    @property
    def symbols_per_frame(self) -> int:
        """每系统帧 OFDM 符号数，由 §4.3.1/§4.3.2 推导。"""
        return self.subframes_per_frame * self.symbols_per_subframe

    @property
    def resource_elements_per_slot(self) -> int:
        """每端口时隙 RE 总数，含参考信号/保留资源；§4.4.2/§4.4.3。"""
        return self.n_subcarriers * self.symbols_per_slot

    @property
    def n_fft(self) -> int:
        """容纳每符号频域 RE 的最小 2**N，至少 128（平台选择规则）。

        只根据载波子载波数选择，不乘符号数、天线数或载波 CRB 偏移。
        128 下限使 R15 所有支持组合的 CP 均对应整数个采样点。
        """
        return max(self.MIN_FFT_SIZE, 1 << (self.n_subcarriers - 1).bit_length())

    @property
    def sample_rate_hz(self) -> int:
        """每个天线分支的采样率 Fs=Nfft·Δf，无重采样；由 §5.3.1 推导。"""
        return self.n_fft * self.subcarrier_spacing_khz * 1000

    @property
    def sample_period_s(self) -> float:
        """实际采样间隔（秒），1/Fs；通常不等于参考时间单位 Ts。"""
        return 1 / self.sample_rate_hz

    @property
    def tc_s(self) -> float:
        """固定时间单位 Tc（秒），1/(480000·4096)；TS 38.211 §4.1。"""
        return 1 / self.TC_FREQUENCY_HZ

    @property
    def ts_s(self) -> float:
        """固定参考 Ts（秒），1/(15000·2048)=64Tc；§4.1。"""
        return 1 / self.TS_FREQUENCY_HZ

    @property
    def tc_per_sample(self) -> int:
        """一个实际采样点对应多少 Tc；本平台自动 FFT 范围内为整数。"""
        return self.TC_FREQUENCY_HZ // self.sample_rate_hz

    @property
    def useful_symbol_length_tc(self) -> int:
        """不含 CP 的符号长度，2048κ·2**(-μ) 个 Tc；§5.3.1。"""
        return (2048 * self.KAPPA) >> self.numerology

    @property
    def cp_lengths_tc(self) -> tuple[int, ...]:
        """一整个子帧各符号的 CP 长度（Tc），按 §5.3.1 原文顺序。

        普通 CP 的长 CP 只位于子帧符号 l=0 和 l=7·2**μ，
        并不是每个 slot 的首符号都有长 CP。扩展 CP 均为 512κ·2**(-μ)。
        """
        if self.cyclic_prefix == "extended":
            return ((512 * self.KAPPA) >> self.numerology,) * self.symbols_per_subframe
        short_cp = (144 * self.KAPPA) >> self.numerology
        second_long = 7 * self.slots_per_subframe
        return tuple(short_cp + (16 * self.KAPPA if symbol in (0, second_long) else 0)
                     for symbol in range(self.symbols_per_subframe))

    @property
    def symbol_lengths_tc(self) -> tuple[int, ...]:
        """一子帧每个符号的总长度（有效部分+CP），单位 Tc；§5.3.1。"""
        return tuple(self.useful_symbol_length_tc + cp for cp in self.cp_lengths_tc)

    @property
    def cp_lengths_samples(self) -> tuple[int, ...]:
        """一子帧逐符号 CP 采样点数，CP 的 Tc 数 / 每采样点 Tc 数。"""
        return tuple(cp // self.tc_per_sample for cp in self.cp_lengths_tc)

    @property
    def symbol_lengths_samples(self) -> tuple[int, ...]:
        """一子帧逐符号总采样点数，含 CP；有效部分固定为 n_fft 点。"""
        return tuple(self.n_fft + cp for cp in self.cp_lengths_samples)

    @property
    def symbol_start_samples(self) -> tuple[int, ...]:
        """一子帧各符号 CP 起点，单位采样点，首个为 0；§5.3.1 递推。"""
        return tuple(accumulate(self.symbol_lengths_samples, initial=0))[:-1]

    @property
    def slot_cp_lengths_samples(self) -> tuple[int, ...]:
        """当前 n_slot 各符号的 CP 采样点数，数量为 symbols_per_slot。"""
        start = self.slot_in_subframe * self.symbols_per_slot
        return self.cp_lengths_samples[start:start + self.symbols_per_slot]

    @property
    def slot_symbol_lengths_samples(self) -> tuple[int, ...]:
        """当前 n_slot 各符号的总采样点数，含 CP。"""
        return tuple(self.n_fft + cp for cp in self.slot_cp_lengths_samples)

    @property
    def slot_start_sample(self) -> int:
        """当前时隙相对所在子帧的精确起点（采样点），不同于平均时长乘法。"""
        return self.symbol_start_samples[self.slot_in_subframe * self.symbols_per_slot]

    @property
    def samples_per_slot(self) -> int:
        """当前时隙总采样点数，含 CP；μ≥2 普通 CP 时可能随时隙变化。"""
        return sum(self.slot_symbol_lengths_samples)

    @property
    def samples_per_subframe(self) -> int:
        """完整 1 ms 子帧的采样点数，Fs/1000；由 §4.3.1 推导。"""
        return self.sample_rate_hz // 1000

    @property
    def samples_per_frame(self) -> int:
        """完整 10 ms 系统帧采样点数，Fs/100；由 §4.3.1 推导。"""
        return self.samples_per_subframe * self.subframes_per_frame

    @property
    def slot_duration_s(self) -> float:
        """当前时隙精确长度（秒），含 CP；不是平均时隙时长。"""
        return self.samples_per_slot / self.sample_rate_hz

    def symbol_timing(self, symbol: int) -> dict[str, int]:
        """查询当前时隙一个符号的 Tc 和采样点信息，依据 §5.3.1。

        Args:
            symbol: 当前时隙内符号索引，0..symbols_per_slot-1。
        Returns:
            符号/子帧编号、CP/有效/总长度及 CP 起点的整数数据。
            *_tc 单位为 Tc，*_samples 和 start_sample_in_subframe 单位为采样点。
        Raises:
            TypeError: symbol 不是 Python int。
            ValueError: symbol 不属于当前时隙。
        """
        _integer("symbol", symbol, 0, self.symbols_per_slot - 1)
        index = self.slot_in_subframe * self.symbols_per_slot + symbol
        start_sample = self.symbol_start_samples[index]
        return {
            "symbol": symbol, "symbol_in_subframe": index,
            "cp_length_tc": self.cp_lengths_tc[index],
            "useful_length_tc": self.useful_symbol_length_tc,
            "total_length_tc": self.symbol_lengths_tc[index],
            "cp_samples": self.cp_lengths_samples[index],
            "useful_samples": self.n_fft,
            "total_samples": self.symbol_lengths_samples[index],
            "start_sample_in_subframe": start_sample,
            "start_tc_in_subframe": start_sample * self.tc_per_sample,
        }

    def prb_to_crb(self, prb: int) -> int:
        """将活动 BWP 内 PRB 转为 CRB，TS 38.211 §4.4.4.4。

        Args:
            prb: BWP 局部 RB 索引，0..bwp_size-1。
        Returns:
            相对 CRB 0 的公共 RB 编号。
        Raises:
            TypeError: prb 不是 Python int。
            ValueError: prb 不属于当前 BWP。
        """
        _integer("prb", prb, 0, self.bwp_size - 1)
        return self.bwp_start + prb

    def crb_to_prb(self, crb: int) -> int:
        """将 CRB 转为活动 BWP 内的 PRB，TS 38.211 §4.4.4.4 逆变换。

        Args:
            crb: 公共 RB 编号，必须位于当前 BWP 的半开 CRB 区间。
        Returns:
            BWP 内从 0 开始的 PRB 索引。
        Raises:
            TypeError: crb 不是 Python int。
            ValueError: crb 不属于当前 BWP，即使它仍属于载波也拒绝。
        """
        _integer("crb", crb, self.bwp_start, self.bwp_start + self.bwp_size - 1)
        return crb - self.bwp_start

    def subcarrier_offset_hz(self, grid_subcarrier: int) -> int:
        """返回网格子载波中心相对 Point A 的频偏（Hz）。

        输入相对载波网格最低子载波，不是 BWP、FFT bin 或载波中心坐标。
        由 TS 38.211 §4.4.4.2/§4.4.4.3 推导。

        Args:
            grid_subcarrier: 载波网格内索引，0..n_subcarriers-1。
        Returns:
            子载波中心相对 Point A 的整数频偏（Hz），不是绝对频率。
        Raises:
            TypeError: 索引不是 Python int。
            ValueError: 索引超出当前载波网格。
        """
        _integer("grid_subcarrier", grid_subcarrier, 0, self.n_subcarriers - 1)
        return (self.n_start_grid * self.SUBCARRIERS_PER_RB + grid_subcarrier) * self.subcarrier_spacing_khz * 1000

    def with_slot_offset(self, offset: int = 1) -> "NRCell":
        """返回前进/后退 offset 个时隙的新配置，跨帧时 SFN 模 1024。

        支持负偏移；只保存循环 SFN，不保留仿真的累计运行帧数。

        Args:
            offset: Python int，默认 1；0 返回等值的新对象，负数向前回溯。
        Returns:
            保留其他配置、按完整帧/时隙编号回绕的新 NRCell。
        Raises:
            TypeError: offset 不是 Python int，含 bool。
        """
        if type(offset) is not int:
            raise TypeError("offset must be an int (bool is not accepted)")
        frame_delta, slot = divmod(self.n_slot + offset, self.slots_per_frame)
        return replace(self, n_frame=(self.n_frame + frame_delta) % self.SFN_MODULUS, n_slot=slot)

    def to_dict(self) -> dict[str, int | str]:
        """返回十二个初始化字段的独立字典；可用 NRCell(**result) 重建。

        BWP 默认值已转为整数，不含派生属性或类常量。修改返回字典不改变原对象。
        """
        return asdict(self)

    def to_matlab_config(self) -> dict[str, int | str]:
        """返回采用 nrCarrierConfig 名称的七个配置参数。

        BWP 不属于该 MATLAB 对象，不导出。本函数只返回普通 Python 字典，
        不调用 MATLAB，也不要求安装 MATLAB Engine。
        """
        return {
            "NCellID": self.n_cell_id,
            "SubcarrierSpacing": self.subcarrier_spacing_khz,
            "CyclicPrefix": self.cyclic_prefix,
            "NSizeGrid": self.n_size_grid,
            "NStartGrid": self.n_start_grid,
            "NFrame": self.n_frame,
            "NSlot": self.n_slot,
        }
