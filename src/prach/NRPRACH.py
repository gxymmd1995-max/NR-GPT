"""One explicitly scheduled R15 PRACH occasion; TS38.211 V15.2.0 §5.3.2/§6.3.3."""

from dataclasses import dataclass
import numpy as np
from cell import NRCell
from common.NRCommon import _integer
from common._validation import real_value
from ._tables import FORMATS, FREQUENCY, NCS, ROOTS_839


@dataclass(frozen=True, slots=True)
class NRPRACH:
    cell: NRCell
    preamble_format: str = "A1"
    subcarrier_spacing_khz: float = 15
    root_sequence_index: int = 0
    zero_correlation_zone: int = 8
    frequency_start: int = 0
    frequency_index: int = 0
    occasion_start_samples: int = 0
    guard_samples: int = 0
    time_origin_samples: int = 0
    restricted_set: str = "unrestricted"

    def __post_init__(self):
        if not isinstance(self.cell, NRCell):
            raise TypeError("cell must be NRCell")
        if (
            not isinstance(self.preamble_format, str)
            or self.preamble_format not in FORMATS
        ):
            raise ValueError("unsupported R15 preamble format")
        scs = real_value("subcarrier_spacing_khz", self.subcarrier_spacing_khz)
        fixed = FORMATS[self.preamble_format][3]
        if (fixed is not None and scs != fixed) or (
            fixed is None and scs not in (15, 30, 60, 120)
        ):
            raise ValueError(
                "format/SCS combination is absent from R15 tables 6.3.3.1-1/-2"
            )
        if (scs, self.cell.subcarrier_spacing_khz) not in FREQUENCY:
            raise ValueError("RA/UL SCS combination is absent from R15 table 6.3.3.2-1")
        if self.restricted_set != "unrestricted":
            raise ValueError("only unrestricted sets are implemented")
        _integer(
            "root_sequence_index", self.root_sequence_index, 0, self.sequence_length - 2
        )
        _integer("zero_correlation_zone", self.zero_correlation_zone, 0, 15)
        _integer("frequency_start", self.frequency_start, 0)
        _integer("frequency_index", self.frequency_index, 0, 7)
        _integer("occasion_start_samples", self.occasion_start_samples, 0)
        _integer("guard_samples", self.guard_samples, 0)
        _integer("time_origin_samples", self.time_origin_samples, 0)
        if (
            self.frequency_start + (self.frequency_index + 1) * self.n_prbs
            > self.cell.bwp_size
        ):
            raise ValueError("PRACH frequency occasion must fit inside the active BWP")
        # Validated NRCell uses power-of-two FFT and R15 SCS. Every admitted pair
        # in table 6.3.3.2-1 yields integer PRACH FFT and CP sample counts.
        # Long-format PRACH FFT is allowed to be 12/24 times the cell FFT.

    @property
    def sequence_length(self):
        return FORMATS[self.preamble_format][0]

    @property
    def repetitions(self):
        return FORMATS[self.preamble_format][1]

    @property
    def n_cs(self):
        return NCS[
            "short" if self.sequence_length == 139 else self.subcarrier_spacing_khz
        ][self.zero_correlation_zone]

    @property
    def n_prbs(self):
        return FREQUENCY[self.subcarrier_spacing_khz, self.cell.subcarrier_spacing_khz][
            0
        ]

    @property
    def k_bar(self):
        return FREQUENCY[self.subcarrier_spacing_khz, self.cell.subcarrier_spacing_khz][
            1
        ]

    @property
    def n_fft(self):
        return int(self.cell.sample_rate_hz / (self.subcarrier_spacing_khz * 1000))

    @property
    def base_cp_tc(self):
        # kappa=64; short-format table uses 2^-mu_RA = 15/SCS_RA.
        factor = 1 if self.sequence_length == 839 else 15 / self.subcarrier_spacing_khz
        return int(FORMATS[self.preamble_format][2] * 64 * factor)

    @property
    def cp_samples(self):
        base = self.base_cp_tc // self.cell.tc_per_sample
        if self.sequence_length == 839:
            return base
        # §5.3.2: add 16*kappa Tc for each half-ms boundary in [start,start+Nu+baseCP).
        half = self.cell.sample_rate_hz // 2000
        start = self.time_origin_samples + self.occasion_start_samples
        count = (start + base + self.repetitions * self.n_fft - 1) // half - (
            start - 1
        ) // half
        return base + count * (16 * 64 // self.cell.tc_per_sample)

    @property
    def active_samples(self):
        return self.cp_samples + self.repetitions * self.n_fft

    @property
    def waveform_samples(self):
        return self.occasion_start_samples + self.active_samples + self.guard_samples

    @property
    def frequency_bins(self):
        # Single-numerology cell: k0^mu=0. Frequency origin is the cell grid center.
        rb = (
            self.cell.bwp_start
            - self.cell.n_start_grid
            + self.frequency_start
            + self.frequency_index * self.n_prbs
        )
        k1 = 12 * rb - 6 * self.cell.n_size_grid
        first = int(
            round(
                k1 * self.cell.subcarrier_spacing_khz / self.subcarrier_spacing_khz
                + self.k_bar
            )
        )
        return first + np.arange(self.sequence_length, dtype=int)

    def preamble_parameters(self, preamble_index):
        """Return (logical root, physical ZC root u, cyclic shift C_v), §6.3.3.1."""
        _integer("preamble_index", preamble_index, 0, 63)
        per_root = max(1, self.sequence_length // self.n_cs) if self.n_cs else 1
        logical = (self.root_sequence_index + preamble_index // per_root) % (
            self.sequence_length - 1
        )
        root = (
            ROOTS_839[logical]
            if self.sequence_length == 839
            else (logical // 2 + 1 if logical % 2 == 0 else 138 - logical // 2)
        )
        return logical, root, (preamble_index % per_root) * self.n_cs

    def sequence(self, preamble_index):
        """Unit-modulus cyclically shifted ZC, complex[L_RA]; positive C advances x."""
        _, root, shift = self.preamble_parameters(preamble_index)
        n = (
            np.arange(self.sequence_length, dtype=np.int64) + shift
        ) % self.sequence_length
        # Reduce the integer phase modulo 2L before float conversion to avoid large-angle loss.
        phase = (root * n * (n + 1)) % (2 * self.sequence_length)
        return np.exp(-1j * np.pi * phase / self.sequence_length)

    def generate(self, preamble_index):
        """Unnormalized DFT, complex[L_RA], magnitude sqrt(L_RA); table-independent FFT."""
        return np.fft.fft(self.sequence(preamble_index))

    def spectrum(self, preamble_index):
        """FFT-order complex[Nfft]; centered physical bins are wrapped modulo Nfft."""
        out = np.zeros(self.n_fft, complex)
        out[self.frequency_bins % self.n_fft] = self.generate(preamble_index)
        return out

    def useful_waveform(self, preamble_index):
        """One period, common-cell sampling; Toolbox-compatible normalization is an amplitude convention."""
        scale = np.sqrt(
            self.cell.subcarrier_spacing_khz
            / self.subcarrier_spacing_khz
            / self.sequence_length
        )
        return np.fft.ifft(self.spectrum(preamble_index)) * scale
