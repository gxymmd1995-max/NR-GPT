"""公共序列算法，固定 TS 38.211 V15.2.0 §5.2.1 / §6.4.1.4.2。"""

import numpy as np


def _integer(name: str, value: int, lower: int, upper: int | None = None) -> None:
    """严格 Python int 校验；lower/upper 是包含端点的范围，None 不设上界。"""
    if type(value) is not int:
        raise TypeError(f"{name} must be a Python int, not bool")
    if value < lower or (upper is not None and value > upper):
        raise ValueError(f"{name} is outside [{lower}, {upper}]")


class NRCommon:
    """无实例状态的静态公共算法集合；通过 NRCommon.method(...) 调用。"""

    GOLD_NC = 1600  # TS 38.211 V15.2.0 §5.2.1：固定丢弃长度，单位 bit。
    GOLD_SEED_BITS = 31  # 两个 m 序列的寄存器级数，不是输出序列长度。

    @staticmethod
    def gold_sequence(c_init: int, length: int, offset: int = 0) -> np.ndarray:
        """生成 §5.2.1 的 uint8 Gold 序列片段 c[offset:offset+length]。

        c_init 为 0..2**31-1 的 Python int，低位先装载到 x2[0:31]。
        length/offset 为非负 Python int，单位 bit；offset 在丢弃 Nc 后计数。
        每次从初始状态独立计算，返回新数组；length=0 返回 (0,)。
        """
        _integer("c_init", c_init, 0, (1 << NRCommon.GOLD_SEED_BITS) - 1)
        _integer("length", length, 0)
        _integer("offset", offset, 0)
        if length == 0:
            return np.empty(0, dtype=np.uint8)
        stop = NRCommon.GOLD_NC + offset + length
        x1 = np.zeros(stop + NRCommon.GOLD_SEED_BITS, dtype=np.uint8)
        x2 = np.zeros_like(x1)
        x1[0] = 1
        x2[:31] = [(c_init >> bit) & 1 for bit in range(31)]
        for n in range(stop):
            x1[n + 31] = x1[n + 3] ^ x1[n]
            x2[n + 31] = x2[n + 3] ^ x2[n + 2] ^ x2[n + 1] ^ x2[n]
        start = NRCommon.GOLD_NC + offset
        return x1[start:stop] ^ x2[start:stop]

    @staticmethod
    def srs_sequence_uv(sequence_id: int, n_slot: int, symbol_start: int, n_symbols: int,
                        sequence_length: int, group_seq_hopping: str = "neither",
                        symbols_per_slot: int = 14) -> dict[str, np.ndarray]:
        """返回 §6.4.1.4.2 的每符号 u/v，新 int64 数组形状均为 (n_symbols,)。

        n_slot 为帧内时隙，支持 0..159（具体 numerology 边界由 NRCell 检查）。
        symbol_start 为时隙内正向符号号，不是 RRC startPosition 反向偏移。
        本接口仅适用于 R15 SRS；不将 SRS 的 u/v 规则套用到其他信道。
        PRBS 每帧以 10bit sequence_id 重新初始化，索引不累计 n_frame。
        """
        for name, value, lower, upper in (
            ("sequence_id", sequence_id, 0, 1023), ("n_slot", n_slot, 0, 159),
            ("symbols_per_slot", symbols_per_slot, 12, 14), ("n_symbols", n_symbols, 1, 4),
            ("sequence_length", sequence_length, 12, 1632)):
            _integer(name, value, lower, upper)
        if symbols_per_slot not in (12, 14):
            raise ValueError("symbols_per_slot must be 12 or 14")
        if n_symbols not in (1, 2, 4):
            raise ValueError("R15 n_symbols must be 1, 2 or 4")
        _integer("symbol_start", symbol_start, symbols_per_slot - 6, symbols_per_slot - n_symbols)
        if sequence_length % 12:
            raise ValueError("R15 SRS sequence_length must be a multiple of 12")
        if not isinstance(group_seq_hopping, str):
            raise TypeError("group_seq_hopping must be a str")
        if group_seq_hopping not in ("neither", "groupHopping", "sequenceHopping"):
            raise ValueError("unknown SRS group_seq_hopping")
        u = np.full(n_symbols, sequence_id % 30, dtype=np.int64)
        v = np.zeros(n_symbols, dtype=np.int64)
        # t 从帧首开始，以 OFDM 符号计数，使用帧内 n_slot。
        symbol = n_slot * symbols_per_slot + symbol_start + np.arange(n_symbols)
        if group_seq_hopping == "groupHopping":
            c = NRCommon.gold_sequence(sequence_id, 8 * n_symbols, offset=8 * int(symbol[0]))
            for l_prime in range(n_symbols):
                # c(8t) 是最低有效位；每组8bit组成整数，再对30取模。
                group = int(np.dot(c[8*l_prime:8*l_prime+8], 2 ** np.arange(8))) % 30
                u[l_prime] = (group + sequence_id) % 30
        elif group_seq_hopping == "sequenceHopping" and sequence_length >= 72:
            v = NRCommon.gold_sequence(sequence_id, n_symbols, offset=int(symbol[0])).astype(np.int64)
        return {"u": u, "v": v}
