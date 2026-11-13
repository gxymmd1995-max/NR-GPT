"""R15 38.211 7.4.1.5, table 7.4.1.5.3-1 rows 1/2: one port, no CDM."""

from dataclasses import dataclass
import numpy as np
from cell import NRCell
from common import NRCommon, NROFDM
from common.NRCommon import _integer
from common._validation import real_value
from grid import NRGrid


@dataclass(frozen=True, slots=True)
class NRCSIRS:
    cell: NRCell
    row: int = 2
    start_rb: int = 0
    n_rbs: int = 24
    symbol: int = 4
    subcarrier: int = 0
    density: float = 1
    rb_parity: int = 0
    scrambling_id: int = 0
    zero_power: bool = False

    def __post_init__(self):
        if not isinstance(self.cell, NRCell):
            raise TypeError("cell must be NRCell")
        _integer("row", self.row, 1, 2)
        _integer("start_rb", self.start_rb, self.cell.n_start_grid)
        _integer("n_rbs", self.n_rbs, 1)
        if self.start_rb + self.n_rbs > self.cell.n_start_grid + self.cell.n_size_grid:
            raise ValueError("CSI-RS CRB allocation must fit carrier")
        _integer("symbol", self.symbol, 2, min(12, self.cell.symbols_per_slot - 1))
        _integer("subcarrier", self.subcarrier, 0, 3 if self.row == 1 else 11)
        real_value("density", self.density)
        if self.density not in ((3,) if self.row == 1 else (0.5, 1)):
            raise ValueError("density does not match R15 row")
        _integer("rb_parity", self.rb_parity, 0, 1)
        _integer("scrambling_id", self.scrambling_id, 0, 1023)
        if type(self.zero_power) is not bool:
            raise TypeError("zero_power must be bool")

    def _points(self):
        # n is the absolute CRB: Gold addressing must not restart at allocation.
        return [
            (n, k)
            for n in range(self.start_rb, self.start_rb + self.n_rbs)
            if self.density != 0.5 or n % 2 == self.rb_parity
            for k in (
                [self.subcarrier + i * 4 for i in range(3)]
                if self.row == 1
                else [self.subcarrier]
            )
        ]

    def indices(self):
        return np.array(
            [
                (0, self.symbol, 12 * (n - self.cell.n_start_grid) + k)
                for n, k in self._points()
            ],
            dtype=int,
        ).reshape(-1, 3)

    def generate(self):
        seed = (
            2**10
            * (self.cell.symbols_per_slot * self.cell.n_slot + self.symbol + 1)
            * (2 * self.scrambling_id + 1)
            + self.scrambling_id
        ) % 2**31
        points = self._points()
        if self.zero_power or not points:
            return np.zeros(len(points), dtype=complex)
        # Batch one Gold interval per symbol; offsets count bits, m counts QPSK points.
        m = np.array(
            [
                int(np.floor(n * self.density) + np.floor(k * self.density / 12))
                for n, k in points
            ],
            dtype=int,
        )
        first, last = int(m[0]), int(m[-1])
        bits = NRCommon.gold_sequence(seed, 2 * (last - first + 1), offset=2 * first)
        iq = 1 - 2 * bits.reshape(-1, 2)[m - first].astype(int)
        return (iq[:, 0] + 1j * iq[:, 1]) / np.sqrt(2)

    def map_to_grid(self, grid, beta=1.0):
        if not isinstance(grid, NRGrid) or grid.cell != self.cell or grid.n_ports != 1:
            raise ValueError("matching single-port NRGrid required")
        beta = real_value("beta", beta, 0)
        return grid.map(self.indices(), beta * self.generate(), owner="CSI_RS")

    def waveform(self, beta=1.0):
        grid = NRGrid(self.cell, 1)
        self.map_to_grid(grid, beta)
        return NROFDM(self.cell).modulate(grid.data)

    def estimate(self, rx_grid):
        """Per-Rx flat LS and received reference power; no calibrated dBm."""
        y = np.asarray(rx_grid, dtype=complex)
        if y.shape != (
            self.cell.n_rx_antennas,
            self.cell.symbols_per_slot,
            self.cell.n_subcarriers,
        ) or not np.all(np.isfinite(y)):
            raise ValueError("finite [Rx,symbol,k] grid required")
        x = self.generate()
        if self.zero_power or not len(x):
            raise ValueError("NZP observations required for channel estimation")
        idx = self.indices()
        obs = y[:, idx[:, 1], idx[:, 2]]
        return dict(
            channel_estimates=np.mean(obs * x.conj(), axis=1),
            rsrp_per_rx=np.mean(abs(obs) ** 2, axis=1),
        )
