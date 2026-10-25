"""NR 频域网格，依据 TS 38.211 V15.2.0 §4.4.1–§4.4.5。

每个实例承载 NRCell 当前时隙，轴为 [逻辑端口, 符号, 载波内子载波]。
资源占用标签是工程管理机制，不等同于规范定义的物理信道类型。
"""

from collections.abc import Sequence

import numpy as np

from cell import NRCell


class NRGrid:
    """提供零初始化、BWP 坐标、原子映射/预留、冲突检查与数据提取。

    端口轴为本实例的局部编号，并非 1000 等协议天线端口编号。
    data/owners 属性返回副本，必须通过 map/reserve/clear 改变网格状态。
    """

    AXIS_ORDER = ("port", "symbol", "subcarrier")
    DOMAIN = "port"
    OWNER_MAX_LENGTH = 64
    DATA_DTYPE = np.complex128

    def __init__(self, cell: NRCell, n_ports: int = 1) -> None:
        """创建一个时隙的复数网格和独立占用标签。

        Args:
            cell: 不可变 NRCell；本实例保留其当前 n_frame/n_slot 配置。
            n_ports: 正 Python int，默认 1，不从物理天线数自动推导。
        Raises:
            TypeError: cell 类型错误，或 n_ports 不是 Python int（包括 bool）。
            ValueError: n_ports 小于 1。
        """
        if not isinstance(cell, NRCell):
            raise TypeError("cell must be an NRCell instance")
        if type(n_ports) is not int:
            raise TypeError("n_ports must be a Python int, not bool")
        if n_ports < 1:
            raise ValueError("n_ports must be >= 1")
        self._cell = cell
        self._n_ports = n_ports
        self._data = np.zeros(self.shape, dtype=self.DATA_DTYPE)
        self._owners = np.full(self.shape, "", dtype=f"U{self.OWNER_MAX_LENGTH}")

    @property
    def cell(self) -> NRCell:
        """当前网格绑定的不可变小区配置，不随新创建的时隙配置自动推进。"""
        return self._cell

    @property
    def n_ports(self) -> int:
        """局部逻辑端口数，与 NRCell.n_tx_antennas 分开管理。"""
        return self._n_ports

    @property
    def n_symbols(self) -> int:
        """当前时隙符号数，普通 CP 为 14、扩展 CP 为 12；§4.3.2。"""
        return self.cell.symbols_per_slot

    @property
    def n_subcarriers(self) -> int:
        """载波子载波数，12×RB；TS 38.211 §4.4.2/§4.4.4.1。"""
        return self.cell.n_subcarriers

    @property
    def shape(self) -> tuple[int, int, int]:
        """返回 (n_ports, n_symbols, n_subcarriers)，不包含 FFT 空子载波。"""
        return (self.n_ports, self.n_symbols, self.n_subcarriers)

    @property
    def data(self) -> np.ndarray:
        """complex128 网格副本，外部修改不改变本实例或占用状态。"""
        return self._data.copy()

    @property
    def owners(self) -> np.ndarray:
        """与 data 同形状的字符串标签副本；空字符串表示未分配。"""
        return self._owners.copy()

    @property
    def occupancy(self) -> np.ndarray:
        """新建的布尔占用数组；由标签判断，不由复数值是否为零判断。"""
        return self._owners != ""

    @property
    def total_re_count(self) -> int:
        """所有端口的 RE 数，不等于数据 RE 数或单端口 RE 数。"""
        return self.n_ports * self.n_symbols * self.n_subcarriers

    @property
    def occupied_re_count(self) -> int:
        """已映射或已预留的 RE 数，包含值为零的已分配 RE。"""
        return int(np.count_nonzero(self.occupancy))

    @property
    def free_re_count(self) -> int:
        """未分配的 RE 数。"""
        return self.total_re_count - self.occupied_re_count

    def _axis(self, values: Sequence[int], name: str, size: int) -> np.ndarray:
        """验证一维唯一整数选择并保留输入顺序；允许空列表。"""
        array = np.asarray(values)
        if array.ndim != 1:
            raise ValueError(f"{name} must be one-dimensional")
        if array.size == 0:
            return np.empty(0, dtype=np.int64)
        if array.dtype.kind not in "iu" or any(isinstance(value, (bool, np.bool_)) for value in np.asarray(values, dtype=object).flat):
            raise TypeError(f"{name} must contain integers, not bool or float")
        if np.any(array < 0) or np.any(array >= size):
            raise ValueError(f"{name} must be in [0, {size - 1}]")
        if len(np.unique(array)) != len(array):
            raise ValueError(f"{name} must not contain duplicates")
        return array.astype(np.int64, copy=True)

    def _indices(self, indices: Sequence[Sequence[int]]) -> np.ndarray:
        """验证 N×3 整数坐标、边界；只读提取允许坐标重复。"""
        array = np.asarray(indices)
        if array.shape == (0,):
            return np.empty((0, 3), dtype=np.int64)
        if array.ndim != 2 or array.shape[1] != 3:
            raise ValueError("indices must have shape (N, 3): [port, symbol, subcarrier]")
        if array.dtype.kind not in "iu" or any(isinstance(value, (bool, np.bool_)) for value in np.asarray(indices, dtype=object).flat):
            raise TypeError("indices must contain integers, not bool or float")
        if np.any(array < 0) or np.any(array >= np.asarray(self.shape)):
            raise ValueError(f"indices are outside grid shape {self.shape}")
        return array.astype(np.int64, copy=True)

    def _owner(self, owner: str) -> str:
        """验证占用标签；拒绝空白、非字符串或超过 64 字符的标签。"""
        if not isinstance(owner, str):
            raise TypeError("owner must be a str")
        if not owner.strip() or len(owner) > self.OWNER_MAX_LENGTH:
            raise ValueError(f"owner must contain 1..{self.OWNER_MAX_LENGTH} nonblank characters")
        return owner

    def _write_indices(self, indices: Sequence[Sequence[int]], owner: str, overwrite: bool) -> np.ndarray:
        """在修改前检查标签、坐标唯一性与已占用冲突，不修改数据。"""
        self._owner(owner)
        if type(overwrite) is not bool:
            raise TypeError("overwrite must be a bool")
        array = self._indices(indices)
        if len(np.unique(array, axis=0)) != len(array):
            raise ValueError("write indices must not contain duplicate REs")
        if not overwrite and np.any(self._owners[tuple(array.T)] != ""):
            raise ValueError("resource collision: RE is already mapped or reserved")
        return array

    def bwp_indices(self, prbs: Sequence[int], symbols: Sequence[int],
                    ports: Sequence[int] | None = None) -> np.ndarray:
        """生成活动 BWP 内 RB 的全部 RE 坐标，依据 §4.4.4.4/§4.4.5。

        prbs 是 BWP 内 PRB 编号；symbols 是当前时隙符号编号；ports 为局部
        端口编号，默认全部。输出 N×3，以端口→符号→输入 PRB→12 子载波排序，
        保留各选择列表的输入顺序。输入类型/越界/重复分别报 TypeError/ValueError。
        """
        prbs = self._axis(prbs, "prbs", self.cell.bwp_size)
        symbols = self._axis(symbols, "symbols", self.n_symbols)
        ports = self._axis(range(self.n_ports) if ports is None else ports, "ports", self.n_ports)
        start = (self.cell.bwp_start - self.cell.n_start_grid) * self.cell.SUBCARRIERS_PER_RB
        rows = [(int(port), int(symbol), start + int(prb) * 12 + subcarrier)
                for port in ports for symbol in symbols for prb in prbs for subcarrier in range(12)]
        return np.asarray(rows, dtype=np.int64).reshape(-1, 3)

    def map(self, indices: Sequence[Sequence[int]], values: object, owner: str,
            overwrite: bool = False) -> int:
        """原子写入复数值并标记占用；全部验证通过后才修改网格。

        values 可为可转换为复数的标量（广播）或与 N 个坐标等长的一维向量。
        NaN/Inf、多维值或长度不符报 ValueError。默认任何已有标签都导致冲突，
        包括相同 owner；只有显式 overwrite=True 才替换。返回写入 RE 数。
        """
        array = self._write_indices(indices, owner, overwrite)
        symbols = np.asarray(values, dtype=self.DATA_DTYPE)
        if not np.all(np.isfinite(symbols)):
            raise ValueError("values must be finite, including for an empty selection")
        if symbols.ndim == 0:
            symbols = np.full(len(array), symbols, dtype=self.DATA_DTYPE)
        if symbols.shape != (len(array),):
            raise ValueError("values must be a finite scalar or a finite vector of length N")
        key = tuple(array.T)
        self._data[key] = symbols
        self._owners[key] = owner
        return len(array)

    def reserve(self, indices: Sequence[Sequence[int]], owner: str) -> int:
        """预留 RE，保持零值并标记占用；不允许覆盖已有资源，返回数量。"""
        array = self._write_indices(indices, owner, False)
        self._owners[tuple(array.T)] = owner
        return len(array)

    def extract(self, indices: Sequence[Sequence[int]]) -> np.ndarray:
        """按给定 N×3 坐标顺序提取复数副本，允许重复，未分配位置返回零。"""
        array = self._indices(indices)
        return self._data[tuple(array.T)].copy()

    def clear(self, owner: str | None = None) -> int:
        """清除指定标签（None 为全部）的值与占用，返回释放的 RE 数。"""
        mask = self.occupancy if owner is None else self._owners == self._owner(owner)
        count = int(np.count_nonzero(mask))
        self._data[mask] = 0
        self._owners[mask] = ""
        return count

    def to_matlab(self) -> np.ndarray:
        """导出 [子载波, 符号, 端口] 复数副本，单端口也保留三维形状。"""
        return self._data.transpose(2, 1, 0).copy()

    def summary(self) -> dict[str, object]:
        """返回配置、轴顺序、数据类型、尺寸和占用数量，不复制整个网格。"""
        return {"cell": self.cell.to_dict(), "n_ports": self.n_ports,
                "domain": self.DOMAIN, "axis_order": self.AXIS_ORDER,
                "shape": self.shape, "dtype": str(self._data.dtype),
                "total_re_count": self.total_re_count, "occupied_re_count": self.occupied_re_count,
                "free_re_count": self.free_re_count}
