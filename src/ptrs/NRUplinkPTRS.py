"""R15 Uplink CP-OFDM single-layer PT-RS resource and phase measurement."""

from dataclasses import dataclass
import numpy as np
from pusch import NRPUSCH
from . import _core


@dataclass(frozen=True, slots=True)
class NRUplinkPTRS:
    resource: NRPUSCH
    time_density: int = 1
    frequency_density: int = 2
    re_offset: int = 0

    def __post_init__(self):
        _core.validate(self, NRPUSCH)

    def indices(self):
        return np.array(_core.positions(self), dtype=int).reshape(-1, 3)

    def generate(self):
        return _core.generate(self)

    def map_to_grid(self, grid, beta=1.0):
        return _core.mapping(self, grid, beta)

    def estimate_phase(self, rx_grid, channel_estimates, *, interpolate=False):
        """Estimate CPE; optionally correct all symbols of the PUSCH allocation."""
        return _core.estimate(self, rx_grid, channel_estimates, interpolate)
