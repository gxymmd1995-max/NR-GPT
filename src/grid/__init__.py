"""单时隙、端口域的 NR 频域资源网格。"""

from grid.NRGrid import NRGrid
from grid.channel_colors import CHANNEL_COLORS, UNKNOWN_COLOR, channel_color, encode_owners

__all__ = ["NRGrid", "CHANNEL_COLORS", "UNKNOWN_COLOR", "channel_color", "encode_owners"]
