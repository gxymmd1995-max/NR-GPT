"""归一化时域信道作用；TA换算固定TS38.213 V15.3.0 §4.2，噪声/CFO为工程模型。"""

from dataclasses import dataclass

import numpy as np

from cell import NRCell
from common.NRCommon import _integer
from common._validation import real_value, waveform_array


@dataclass(frozen=True, slots=True)
class NRChannel:
    """无内部流状态；波形统一[branch,sample]，时间/随机种子由调用者显式传入。"""

    cell: NRCell

    def __post_init__(self):
        if not isinstance(self.cell, NRCell):
            raise TypeError("cell must be an NRCell")

    def timing_advance(self, waveform: np.ndarray, ta_samples: int) -> np.ndarray:
        """正TA提前：y[n]=x[n+TA]；负TA延迟。保持形状，越界补零，不循环回绕。

        仅整数样点；有限捕获窗口边缘可能被裁掉，须由上层留足保护区。
        """
        values = waveform_array(waveform)
        _integer("ta_samples", ta_samples, -values.shape[1], values.shape[1])
        if ta_samples == 0:
            return values.copy()
        result = np.zeros_like(values)
        if ta_samples > 0:
            result[:, : values.shape[1] - ta_samples] = values[:, ta_samples:]
        else:
            result[:, -ta_samples:] = values[:, : values.shape[1] + ta_samples]
        return result

    def ta_command_samples(self, command: int, initial: bool = False) -> int:
        """§4.2：相对MAC TA(0..63)返回增量；RAR初始TA(0..3846)返回绝对量。

        一步=16*64/2^mu Tc=Nfft/128样点。未应用N_TA_offset/TAG生效时序。
        """
        if type(initial) is not bool:
            raise TypeError("initial must be bool")
        _integer("command", command, 0, 3846 if initial else 63)
        return (command - (0 if initial else 31)) * (self.cell.n_fft // 128)

    def frequency_offset(
        self,
        waveform: np.ndarray,
        frequency_offset_hz: float,
        initial_phase_rad: float = 0.0,
        start_sample: int = 0,
    ) -> np.ndarray:
        """乘exp(j*(phase+2π*Δf*(start+n)/Fs))；正频偏提高频率。

        start_sample为连续时间样点号，跨块调用需累加以保持相位连续；与NR符号相位分开。
        """
        values = waveform_array(waveform)
        offset = real_value("frequency_offset_hz", frequency_offset_hz)
        phase = real_value("initial_phase_rad", initial_phase_rad)
        _integer("start_sample", start_sample, 0)
        if abs(offset) >= self.cell.sample_rate_hz / 2:
            raise ValueError(
                "frequency_offset_hz must be inside the sample-rate Nyquist interval"
            )
        time_samples = start_sample + np.arange(values.shape[1])
        rotation = np.exp(
            1j * (phase + 2 * np.pi * offset * time_samples / self.cell.sample_rate_hz)
        )
        return values * rotation[None, :]

    def add_awgn(
        self,
        waveform: np.ndarray,
        snr_db: float,
        *,
        seed: int | None = None,
        noise_standard: np.ndarray | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        """按每接收支路的整段波形平均功率和SNR(dB)加复AWGN，返回(波形,噪声)。

        Pn[b]=mean(|x[b]|²)*10**(-snr_db/10)，包括静默样点；零功率支路噪声为零。
        noise_standard为单位复方差参考向量，与seed互斥；不重标定有限噪声样本功率。
        """
        values = waveform_array(waveform)
        snr = real_value("snr_db", snr_db)
        if values.shape[1] == 0:
            raise ValueError("waveform must contain samples to measure signal power")
        # 在对数域缩放，避免高/低SNR导致中间比例溢出；最终方差必须可表示。
        with np.errstate(
            over="ignore", under="ignore", divide="ignore", invalid="ignore"
        ):
            signal_power = np.mean(np.abs(values) ** 2, axis=1)
            power = np.exp(np.log(signal_power) - snr * np.log(10) / 10)
        if not np.all(np.isfinite(power)) or np.any((signal_power > 0) & (power == 0)):
            raise ValueError("snr_db produces an unrepresentable noise variance")
        if seed is not None:
            _integer("seed", seed, 0)
        if noise_standard is not None:
            if seed is not None:
                raise ValueError("noise_standard and seed are mutually exclusive")
            standard = waveform_array(noise_standard)
            if standard.shape != values.shape:
                raise ValueError("noise_standard must match waveform shape")
        else:
            rng = np.random.default_rng(seed)
            standard = (
                rng.standard_normal(values.shape)
                + 1j * rng.standard_normal(values.shape)
            ) / np.sqrt(2)
        noise = standard * np.sqrt(power[:, None])
        return values + noise, noise
