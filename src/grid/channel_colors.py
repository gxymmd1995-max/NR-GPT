"""统一资源网格配色：项目显示约定，不属于 3GPP 协议参数。

颜色与幅度、端口、绘制顺序无关，按 owner 标签分类；参考同级 channel_colors.md。
"""

from types import MappingProxyType

import numpy as np


CHANNEL_COLORS = MappingProxyType({
    "FREE": "#F8FAFC", "RESERVED": "#94A3B8",
    "SSB": "#E69F00", "PDCCH": "#0072B2", "PDSCH": "#009E73",
    "PUSCH": "#9467BD", "PUCCH": "#D55E00", "PRACH": "#56B4E9", "SRS": "#8C564B",
    "DMRS": "#F0E442", "PTRS": "#E377C2", "CSI_RS": "#17BECF",
    "PSS": "#B8860B", "SSS": "#BCBD22", "PBCH": "#FF7F0E",
    "STREAM_A": "#3B82F6", "STREAM_B": "#10B981", "ZERO": "#EF4444",
})
UNKNOWN_COLOR = "#6B7280"
_ALIASES = {"DM_RS": "DMRS", "PT_RS": "PTRS", "SS/PBCH": "SSB", "SS_PBCH": "SSB"}


def _channel_name(owner: str) -> str:
    """将 owner 归一化为显示类别；支持 PDSCH:UE0 等标签及常用参考信号别名。"""
    if not isinstance(owner, str):
        raise TypeError("owner must be a str")
    raw = owner.strip()
    if not raw:
        return "FREE"
    name = (raw.partition(":")[0].strip() or raw).upper().replace("-", "_")
    return _ALIASES.get(name, name)


def channel_color(owner: str) -> str:
    """返回类别的固定 HEX 颜色，未知类别灰色；不根据功率或调用顺序改变颜色。"""
    return CHANNEL_COLORS.get(_channel_name(owner), UNKNOWN_COLOR)


def encode_owners(owners: np.ndarray) -> tuple[np.ndarray, tuple[str, ...], tuple[str, ...]]:
    """将二维/三维 Unicode owner 数组转为离散颜色索引、标签和颜色表。

    不修改输入。别名与 UE 后缀归并到同一类别，已知类别按固定表排序，未知
    类别按名称排序并用灰色。拒绝空数组、非二维/三维数组及非 Unicode 数组。
    codes 与 owners 同形状，labels[codes[p,l,k]] 是该 RE 的显示类别。
    """
    array = np.asarray(owners)
    if array.ndim not in (2, 3) or array.size == 0:
        raise ValueError("owners must be a nonempty 2-D or 3-D array")
    if array.dtype.kind != "U":
        raise TypeError("owners must be a Unicode string array")
    names = {owner: _channel_name(owner) for owner in np.unique(array).tolist()}
    categories = set(names.values())
    labels = tuple(name for name in CHANNEL_COLORS if name in categories)
    labels += tuple(sorted(categories.difference(CHANNEL_COLORS)))
    positions = {label: index for index, label in enumerate(labels)}
    codes = np.empty(array.shape, dtype=np.int64)
    for owner, name in names.items():
        codes[array == owner] = positions[name]
    colors = tuple(channel_color(label) for label in labels)
    return codes, labels, colors
