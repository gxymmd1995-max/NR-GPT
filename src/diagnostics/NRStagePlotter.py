"""在内存记录实际变换结果，分组显示Matplotlib图窗；不写图像文件。"""

from fnmatch import fnmatchcase

import numpy as np

from diagnostics.NRPlotConfig import NRPlotConfig


class NRStagePlotter:
    """关闭或过滤时不复制数组；Matplotlib只在figures/show调用且确有记录时导入。"""

    def __init__(self, config: NRPlotConfig | None = None, prefix: str = ""):
        self.config = NRPlotConfig() if config is None else config
        if not isinstance(self.config, NRPlotConfig):
            raise TypeError("config must be NRPlotConfig")
        if not isinstance(prefix, str):
            raise TypeError("prefix must be str")
        self.prefix = prefix
        self._records = []

    @property
    def stages(self) -> tuple[str, ...]:
        """返回实际选中阶段名，不暴露内部数组。"""
        return tuple(item[0] for item in self._records)

    def record(
        self,
        stage: str,
        values,
        *,
        kind: str = "waveform",
        title: str = "",
        xlabel: str = "Sample",
        ylabel: str = "Normalized amplitude",
        labels=None,
        branch_prefix: str = "Rx",
    ):
        """选中时复制实际结果；kind为waveform/sequence/grid/metric/constellation，无文件系统操作。

        波形/序列为[B,N]或[N]，网格为[B,L,K]，metric为[N]实数。
        禁用时在转换values前返回，避免诊断产生额外数组或绘图依赖。
        """
        name = f"{self.prefix}.{stage}" if self.prefix else stage
        if not self.config.enabled:
            return
        if self.config.stages is not None and not any(
            fnmatchcase(name, p) for p in self.config.stages
        ):
            return
        if kind not in ("waveform", "sequence", "grid", "metric", "constellation"):
            raise ValueError("unknown stage plot kind")
        data = np.asarray(values)
        valid = (
            (data.ndim == 3 and min(data.shape) > 0)
            if kind == "grid"
            else (data.ndim == 1 if kind == "metric" else data.ndim in (1, 2))
        )
        if not valid or not np.all(np.isfinite(data)):
            raise ValueError(
                "stage values must be finite and match the requested plot axes"
            )
        if labels is not None and len(labels) != data.shape[-1]:
            raise ValueError("labels must match the final array axis")
        if not isinstance(branch_prefix, str) or not branch_prefix.strip():
            raise ValueError("branch_prefix must be a nonempty string")
        self._records.append(
            (
                name,
                data.copy(),
                kind,
                title,
                xlabel,
                ylabel,
                None if labels is None else tuple(labels),
                branch_prefix,
            )
        )

    def figures(self):
        """生成内存Figure列表，不调用show，不保存；调用方可嵌入自己的界面或关闭图窗。"""
        if not self._records:
            return []
        import matplotlib.pyplot as plt
        from matplotlib.colors import LinearSegmentedColormap
        from grid import channel_color

        color = channel_color(self.config.channel)
        cmap = LinearSegmentedColormap.from_list("nr_channel", ["#F8FAFC", color])
        figures = []
        size = self.config.panels_per_figure
        for start in range(0, len(self._records), size):
            records = self._records[start : start + size]
            cols = min(2, len(records))
            rows = (len(records) + cols - 1) // cols
            fig, axes = plt.subplots(
                rows,
                cols,
                figsize=(7 * cols, 3.2 * rows),
                layout="constrained",
                squeeze=False,
            )
            fig.suptitle(
                f"{self.config.channel} transform stages | {self.prefix or 'single call'} | page {start//size+1}"
            )
            for ax, item in zip(axes.flat, records):
                name, data, kind, title, xlabel, ylabel, labels, branch_prefix = item
                ax.set_title(f"{name}\n{title}", fontsize=9)
                if kind == "grid":
                    power = np.mean(np.abs(data) ** 2, axis=0)
                    length = power.shape[0]
                    height = power.shape[1]
                    im = ax.imshow(
                        10 * np.log10(np.maximum(power, 1e-12)).T,
                        origin="lower",
                        aspect="auto",
                        interpolation="nearest",
                        cmap=cmap,
                        extent=(-0.5, length - 0.5, -0.5, height - 0.5),
                    )
                    phase = np.ma.masked_where(np.abs(data[0]) == 0, np.angle(data[0]))
                    phase_im = ax.imshow(
                        phase.T,
                        origin="lower",
                        aspect="auto",
                        interpolation="nearest",
                        cmap="twilight",
                        vmin=-np.pi,
                        vmax=np.pi,
                        extent=(length + 0.5, 2 * length + 0.5, -0.5, height - 0.5),
                    )
                    ax.set(
                        xlim=(-0.5, 2 * length + 0.5),
                        xlabel=xlabel + " (power left / B0 phase right)",
                        ylabel=ylabel,
                    )
                    ax.set_xticks(
                        [0, length - 1, length + 1, 2 * length],
                        ["0", str(length - 1), "0", str(length - 1)],
                        fontsize=7,
                    )
                    fig.colorbar(
                        im, ax=ax, label="Mean power (dB)", fraction=0.025, pad=0.01
                    )
                    fig.colorbar(
                        phase_im,
                        ax=ax,
                        label="B0 phase (rad)",
                        fraction=0.025,
                        pad=0.08,
                    )
                elif kind == "constellation":
                    branches = np.atleast_2d(data)
                    length = branches.shape[-1]
                    points = np.linspace(
                        0,
                        max(length - 1, 0),
                        min(length, self.config.max_points),
                        dtype=int,
                    )
                    for branch in range(
                        min(branches.shape[0], self.config.max_branches)
                    ):
                        y = branches[branch, points]
                        ax.scatter(
                            y.real,
                            y.imag,
                            label=f"{branch_prefix}{branch}",
                            color=color,
                            marker=("o", "x", "s", "d")[branch % 4],
                            s=48,
                        )
                        if labels is not None:
                            for index, value in zip(points, y):
                                ax.annotate(
                                    str(labels[index]),
                                    (value.real, value.imag),
                                    xytext=(4, 4),
                                    textcoords="offset points",
                                    fontsize=7,
                                )
                    ax.axhline(0, color="#94A3B8", lw=0.7)
                    ax.axvline(0, color="#94A3B8", lw=0.7)
                    ax.set(xlabel=xlabel, ylabel=ylabel, aspect="equal")
                    ax.grid(alpha=0.2)
                    ax.legend(fontsize=8)
                elif kind == "metric":
                    ax.bar(np.arange(data.size), data.real, color=color)
                    if labels is not None:
                        ax.set_xticks(
                            np.arange(data.size), labels, rotation=25, fontsize=8
                        )
                    ax.set(xlabel=xlabel, ylabel=ylabel)
                else:
                    branches = np.atleast_2d(data)
                    length = branches.shape[-1]
                    points = np.linspace(
                        0,
                        max(length - 1, 0),
                        min(length, self.config.max_points),
                        dtype=int,
                    )
                    for branch in range(
                        min(branches.shape[0], self.config.max_branches)
                    ):
                        y = branches[branch, points]
                        ax.plot(
                            points,
                            y.real,
                            label=f"B{branch} I",
                            lw=0.8,
                            color=color,
                            alpha=1 / (1 + 0.3 * branch),
                        )
                        ax.plot(
                            points,
                            y.imag,
                            label=f"B{branch} Q",
                            lw=0.8,
                            color=color,
                            ls="--",
                            alpha=0.65,
                        )
                        ax.plot(
                            points,
                            abs(y),
                            label=f"B{branch} magnitude",
                            lw=0.7,
                            color="#64748B",
                            alpha=0.5,
                        )
                    if length == 0:
                        ax.text(
                            0.5,
                            0.5,
                            "DTX: no sequence points",
                            ha="center",
                            transform=ax.transAxes,
                        )
                    ax.set(xlabel=xlabel, ylabel=ylabel)
                    ax.text(
                        0.01,
                        0.98,
                        f"shape={data.shape}; shown {len(points)}/{length} points; first {min(branches.shape[0],self.config.max_branches)} branches",
                        va="top",
                        transform=ax.transAxes,
                        fontsize=7,
                    )
                    if length:
                        ax.legend(fontsize=6, ncol=3, loc="lower right")
            for ax in list(axes.flat)[len(records) :]:
                ax.set_visible(False)
            figures.append(fig)
        return figures

    def show(self, *, block: bool = False):
        """直接显示选中阶段，默认非阻塞；脚本入口可在最后使用plt.show()保持图窗。"""
        figures = self.figures()
        if figures:
            import matplotlib.pyplot as plt

            plt.show(block=block)
        return figures
