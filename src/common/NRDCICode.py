"""TS38.212 V15.2.0 §7.3.2: CRC24C/RNTI, interleaved Polar and rate matching; SC decode."""

from dataclasses import dataclass
import json, math
from pathlib import Path
import numpy as np
from common.NRCommon import _integer
from common.NRPolarCode import NRPolarCode
from common.NRUCICode import SUBBLOCK


@dataclass(frozen=True)
class NRDCICode:
    n_bits: int
    output_length: int
    rnti: int = 1

    def __post_init__(self):
        _integer("n_bits", self.n_bits, 12, 140)
        _integer("output_length", self.output_length, self.n_bits + 24, 1728)
        _integer("rnti", self.rnti, 0, 65535)

    @property
    def n_blocks(self):
        return 1

    @property
    def crc_length(self):
        return 24

    def crc(self, bits):
        # §7.3.2.1: prefix 24 ones; mask only the final 16 CRC bits with MSB-first RNTI.
        work = np.concatenate(
            [np.ones(24, dtype=np.int8), bits, np.zeros(24, dtype=np.int8)]
        )
        poly = np.array(
            [(0x1B2B117 >> i) & 1 for i in range(24, -1, -1)], dtype=np.int8
        )
        for i in range(24 + len(bits)):
            if work[i]:
                work[i : i + 25] ^= poly
        crc = work[-24:].copy()
        crc[-16:] ^= np.array(
            [(self.rnti >> i) & 1 for i in range(15, -1, -1)], dtype=np.int8
        )
        return crc

    def polar_configuration(self):
        k = math.ceil(self.n_bits / self.n_blocks) + self.crc_length
        e = self.output_length // self.n_blocks
        n1 = math.ceil(math.log2(e))
        if e <= 9 / 8 * 2 ** (n1 - 1) and k / e < 9 / 16:
            n1 -= 1
        n = max(5, min(n1, math.ceil(math.log2(8 * k)), 9))
        N = 2**n
        pc = 0
        wm = int(pc > 0 and e - k + 3 > 192)
        j = (
            SUBBLOCK[np.arange(N) // (N // 32)] * (N // 32) + np.arange(N) % (N // 32)
        ).astype(int)
        forbidden = set()
        if e < N:
            if k / e <= 7 / 16:
                forbidden.update(j[: N - e])
                limit = (
                    math.ceil(3 * N / 4 - e / 2)
                    if e >= 3 * N / 4
                    else math.ceil(9 * N / 16 - e / 4)
                )
                forbidden.update(range(limit))
            else:
                forbidden.update(j[e:])
        reliability = json.loads(
            Path(__file__).with_name("_coding_tables.json").read_text()
        )["reliability"]
        available = [v for v in reliability if v < N and v not in forbidden]
        if len(available) < k + pc or k + pc > e:
            raise ValueError("insufficient Polar resources")
        selected = available[-k:]
        return k, e, N, j, np.sort(selected), set()

    def encode(self, bits):
        v = np.asarray(bits)
        if (
            v.shape != (self.n_bits,)
            or v.dtype.kind not in "iu"
            or np.any((v != 0) & (v != 1))
        ):
            raise ValueError("binary DCI payload [A] required")
        k, e, N, j, indices, _ = self.polar_configuration()
        permutation = NRPolarCode(k, N, True).permutation()
        message = np.concatenate([v, self.crc(v)])[permutation]
        u = np.zeros(N, dtype=np.int8)
        u[indices] = message
        y = NRPolarCode.transform(u)[j]
        return (
            y[np.arange(e) % N] if e >= N else y[N - e :] if k / e <= 7 / 16 else y[:e]
        )

    def decode(self, llr):
        values = np.asarray(llr, dtype=float)
        if values.shape != (self.output_length,) or not np.all(np.isfinite(values)):
            raise ValueError("finite soft input [E] required")
        k, e, N, j, indices, _ = self.polar_configuration()
        y = np.zeros(N)
        if e >= N:
            np.add.at(y, np.arange(e) % N, values)
        elif k / e <= 7 / 16:
            y[N - e :] = values
        else:
            y[:e] = values
            y[e:] = 1e6
        a = np.empty(N)
        a[j] = y
        decisions = np.zeros(N, dtype=np.int8)
        info = set(indices)

        def visit(v, offset):
            if len(v) == 1:
                bit = int(v[0] < 0) if offset in info else 0
                decisions[offset] = bit
                return np.array([bit], dtype=np.int8)
            half = len(v) // 2
            l = v[:half]
            r = v[half:]
            left = visit(np.sign(l) * np.sign(r) * np.minimum(abs(l), abs(r)), offset)
            right = visit(r + (1 - 2 * left) * l, offset + half)
            return np.concatenate([left ^ right, right])

        visit(a, 0)
        message = np.empty(k, dtype=np.int8)
        message[NRPolarCode(k, N, True).permutation()] = decisions[indices]
        return dict(
            bits=message[:-24].tolist(),
            crc_ok=bool(np.array_equal(self.crc(message[:-24]), message[-24:])),
        )
