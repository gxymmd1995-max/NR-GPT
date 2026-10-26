"""时域公共模块的内部数值/数组校验；单位由调用者docstring说明。"""

import numpy as np


def real_value(name, value, lower=None, upper=None):
    """校验有限实数，拒绝bool；返回float，区间端点包含。"""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a real number, not bool")
    if not np.isfinite(value) or (lower is not None and value < lower) or (upper is not None and value > upper):
        raise ValueError(f"{name} must be finite and within [{lower},{upper}]")
    return float(value)


def waveform_array(waveform):
    """转为有限complex128 [branch,sample]，允许空采样块，不修改输入。"""
    values = np.asarray(waveform, dtype=np.complex128)
    if values.ndim != 2 or values.shape[0] < 1 or not np.all(np.isfinite(values)):
        raise ValueError("waveform must be finite [branch,sample], with at least one branch")
    return values
