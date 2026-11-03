"""同一复平面显示12种循环移位；只显示图像，不保存图片或数值文件。

依据TS38.211 V15.2.0 §5.2.2.2、§6.3.2.2/3：
实际12点序列除以同根零移位序列后，在n=1处得到exp(j*2*pi*k/12)。
这是循环移位相位因子示意，不是12UE并发译码或相关后信道星座。
"""

import numpy as np

from common import NRCommon
from diagnostics import ExampleLogger, NRPlotConfig


def build_data():
    """返回实际序列与相位点；固定根u=0，不加入公共Gold跳变。

    shifts: int[12]，有效移位索引0..11；alpha_rad: float[12]，rad。
    sequences: complex[12,12]，轴为移位k/频率序号n，归一化幅度。
    phase_factors: complex[12,12]，除去基础序列后的单位模因子。
    points: complex[12]，phase_factors[:,1]，无量纲单位圆坐标。
    """
    shifts = np.arange(12)
    sequences = np.array([NRCommon.low_papr_sequence_12(0, int(k)) for k in shifts])
    base = NRCommon.low_papr_sequence_12(0)
    factors = sequences / base[None, :]
    return dict(shifts=shifts, alpha_rad=2*np.pi*shifts/12,
                sequences=sequences, phase_factors=factors, points=factors[:, 1])


def main(log=None, plot_config=None):
    """默认显示一张12点圆图，返回build_data字典；enabled=False时不导入绘图库。

    log为可选ExampleLogger，plot_config为可选NRPlotConfig；只使用enabled字段。
    调用方负责plt.show()阻塞等待；本函数使用非阻塞显示以便交互使用。
    """
    data = build_data()
    if log is not None:
        log.logger.info('12 cyclic shifts, n=1 after base-sequence removal; angles_deg=%s',
                        np.rad2deg(data['alpha_rad']).tolist())
    config = NRPlotConfig(enabled=True) if plot_config is None else plot_config
    if not config.enabled:
        return data

    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(9, 9), layout='constrained')
    angle = np.linspace(0, 2*np.pi, 361)
    ax.plot(np.cos(angle), np.sin(angle), color='#94a3b8', linewidth=1)
    colors = plt.get_cmap('hsv')(np.arange(12)/12)
    for k, point, color in zip(data['shifts'], data['points'], colors):
        ax.plot([0, point.real], [0, point.imag], color=color, alpha=.35, linewidth=1)
        ax.scatter(point.real, point.imag, color=color, edgecolor='#334155', s=95, zorder=3)
        ax.text(1.18*point.real, 1.18*point.imag, f'k={k}\n{30*k} deg',
                ha='center', va='center', fontsize=10)
    ax.axhline(0, color='#94a3b8', linewidth=.7)
    ax.axvline(0, color='#94a3b8', linewidth=.7)
    ax.set(xlim=(-1.42, 1.42), ylim=(-1.42, 1.42),
           xlabel='I (dimensionless)', ylabel='Q (dimensionless)',
           title='PUCCH F0: all 12 cyclic-shift phase factors\n'
                 r'$r_k[1]/r_0[1]=e^{j2\pi k/12}$; base sequence removed, n=1')
    ax.set_aspect('equal')
    ax.grid(alpha=.2)
    plt.show(block=False)
    return data


if __name__ == '__main__':
    plot_config = NRPlotConfig(enabled=True)
    with ExampleLogger(__file__) as run:
        main(run, plot_config)
    if plot_config.enabled:
        import matplotlib.pyplot as plt
        plt.show()
