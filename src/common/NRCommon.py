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


    @staticmethod
    def low_papr_sequence_12(group: int, cyclic_shift: int = 0) -> np.ndarray:
        """TS38.211 V15.2.0 §5.2.2.2表5.2.2.2-2；12点单位模序列，新complex128[12]。

        group=u∈0..29；cyclic_shift∈0..11，逐点相位增量2*pi*shift/12(rad)。
        12点基序列不依赖v；不复制MATLAB生成的表，原SRS亦复用此表常量。
        """
        from common._low_papr_tables import PHI_12
        _integer("group", group, 0, 29)
        _integer("cyclic_shift", cyclic_shift, 0, 11)
        return np.exp(1j*(np.asarray(PHI_12[group])*np.pi/4
                          + 2*np.pi*cyclic_shift*np.arange(12)/12))

    @staticmethod
    def pucch_sequence_parameters(hopping_id: int, n_slot: int, symbol_start: int,
                                  n_symbols: int, initial_cyclic_shift: int = 0,
                                  m_cs: int = 0, group_hopping: str = "neither",
                                  frequency_hopping: bool = False,
                                  symbols_per_slot: int = 14) -> dict[str, np.ndarray]:
        """固定R15 §6.3.2.2的PUCCH逐符号参数；不是SRS u/v规则。

        slot帧内编号；symbol_start是slot正向索引；结果每项[n_symbols]。
        返回u/v、hop、8bit n_cs、mod12 cyclic_shift和alpha(rad/序列点)。
        F0仅1/2符号；频跳需2符号。循环移位PRBS寻址固定14*slot，不因extended CP改12。
        """
        for name, value, lo, hi in (
            ("hopping_id",hopping_id,0,1023),("n_slot",n_slot,0,159),
            ("n_symbols",n_symbols,1,2),("initial_cyclic_shift",initial_cyclic_shift,0,11),
            ("m_cs",m_cs,0,11),("symbols_per_slot",symbols_per_slot,12,14)):
            _integer(name,value,lo,hi)
        if symbols_per_slot not in (12,14):
            raise ValueError("symbols_per_slot must be 12 or 14")
        if symbols_per_slot == 12 and n_slot > 39:
            raise ValueError("extended CP n_slot must be at most 39")
        _integer("symbol_start",symbol_start,0,symbols_per_slot-n_symbols)
        if group_hopping not in ("neither","enable","disable"):
            raise ValueError("group_hopping must be neither, enable or disable")
        if type(frequency_hopping) is not bool:
            raise TypeError("frequency_hopping must be bool")
        if frequency_hopping and n_symbols != 2:
            raise ValueError("F0 intra-slot hopping requires two symbols")
        hop = np.arange(n_symbols,dtype=np.int64) if frequency_hopping else np.zeros(n_symbols,dtype=np.int64)
        u = np.full(n_symbols,hopping_id%30,dtype=np.int64)
        v = np.zeros(n_symbols,dtype=np.int64)
        for index, nhop in enumerate(hop):
            t = 2*n_slot+int(nhop)
            if group_hopping == "enable":
                bits = NRCommon.gold_sequence(hopping_id//30,8,offset=8*t)
                u[index] = (int(bits @ (2**np.arange(8)))+hopping_id)%30
            elif group_hopping == "disable":
                seed = 32*(hopping_id//30)+hopping_id%30
                v[index] = int(NRCommon.gold_sequence(seed,1,offset=t)[0])
        bits = NRCommon.gold_sequence(hopping_id,8*n_symbols,offset=8*(14*n_slot+symbol_start))
        n_cs = bits.reshape(n_symbols,8).astype(np.int64) @ (2**np.arange(8))
        shift = (initial_cyclic_shift+m_cs+n_cs)%12
        return {"u":u,"v":v,"hop":hop,"n_cs":n_cs,"cyclic_shift":shift,
                "alpha":2*np.pi*shift/12}
