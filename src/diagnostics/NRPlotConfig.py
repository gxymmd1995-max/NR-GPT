"""交互绘图配置；默认关闭，不指定任何图像输出路径。"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NRPlotConfig:
    """stages使用fnmatch通配符；只控制显示，不影响数值处理或保存图片。"""

    enabled: bool = False
    stages: tuple[str, ...] | None = None
    max_points: int = 2000
    panels_per_figure: int = 6
    max_branches: int = 4
    channel: str = "PUCCH"

    def __post_init__(self):
        if type(self.enabled) is not bool:
            raise TypeError("enabled must be bool")
        if self.stages is not None:
            if not isinstance(self.stages, tuple) or any(not isinstance(x,str) or not x for x in self.stages):
                raise ValueError("stages must be None or a tuple of nonempty glob patterns")
        for name,lower in (("max_points",16),("panels_per_figure",1),("max_branches",1)):
            value=getattr(self,name)
            if type(value) is not int:
                raise TypeError(f"{name} must be a Python int")
            if value<lower:
                raise ValueError(f"{name} must be at least {lower}")
        if self.panels_per_figure>9:
            raise ValueError("panels_per_figure must be at most 9")
        if not isinstance(self.channel,str) or not self.channel:
            raise ValueError("channel must be a nonempty physical-channel label")
