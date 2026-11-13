"""重新比较真实MATLAB OFDM/相位及channel输入，保存数值报告。"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np

from cell import NRCell
from common import NROFDM, NRPhaseRotation
from channel import NRChannel
from diagnostics import ExampleLogger


def compare(log):
    """全向量断言通过才输出NROFDM_comparison.json；含两类参考和实现哈希。"""
    output = Path(__file__).resolve().parent
    root = output.parents[1]
    paths = [
        output / "NROFDM_reference.json",
        root / "examples/channel/NRChannel_reference.json",
    ]
    ofdm = json.loads(paths[0].read_text(encoding="utf-8-sig"))
    channel = json.loads(paths[1].read_text(encoding="utf-8-sig"))
    max_wave = max_demod = max_phase = max_channel = 0.0
    ofdm_cases = []
    for index, case in enumerate(ofdm["cases"]):
        x, e = case["input"], case["expected"]
        cell = NRCell(**x["cell"])
        p = x["n_branches"]
        model = NROFDM(cell, x["carrier_frequency_hz"])
        grid = (np.array(x["grid_real"]) + 1j * np.array(x["grid_imag"])).reshape(
            p, cell.symbols_per_slot, cell.n_subcarriers
        )
        target = (np.array(e["wave_real"]) + 1j * np.array(e["wave_imag"])).reshape(
            p, e["n_samples"]
        )
        wave = model.modulate(grid)
        np.testing.assert_allclose(wave, target, rtol=0, atol=2e-9)
        err = float(np.max(abs(wave - target)))
        max_wave = max(max_wave, err)
        phases = NRPhaseRotation(cell, x["carrier_frequency_hz"]).symbol_phases()
        np.testing.assert_allclose(phases, e["symbol_phases"], rtol=0, atol=2e-8)
        max_phase = max(max_phase, float(np.max(abs(phases - e["symbol_phases"]))))
        probe = (np.array(x["probe_real"]) + 1j * np.array(x["probe_imag"])).reshape(
            target.shape
        )
        for item in e["demod"]:
            expected = (np.array(item["real"]) + 1j * np.array(item["imag"])).reshape(
                grid.shape
            )
            actual = model.demodulate(probe, item["cp_fraction"])
            np.testing.assert_allclose(actual, expected, rtol=0, atol=3e-8)
            max_demod = max(max_demod, float(np.max(abs(actual - expected))))
        ofdm_cases.append({"case_id": index, "wave_max_abs_error": err})
    for case in channel["cases"]:
        x, e = case["input"], case["expected"]
        model = NRChannel(NRCell(**x["cell"]))
        shape = (x["n_branches"], x["n_samples"])

        def values(obj, prefix):
            return (
                np.array(obj[prefix + "real"]) + 1j * np.array(obj[prefix + "imag"])
            ).reshape(shape)

        shifted = model.timing_advance(values(x, ""), x["ta_samples"])
        np.testing.assert_array_equal(shifted, values(e, "shift_"))
        rotated = model.frequency_offset(
            shifted, x["frequency_offset_hz"], x["initial_phase_rad"], x["start_sample"]
        )
        result, noise = model.add_awgn(
            rotated, x["snr_db"], noise_standard=values(x, "standard_")
        )
        np.testing.assert_allclose(rotated, values(e, "rotated_"), rtol=0, atol=1e-12)
        np.testing.assert_allclose(noise, values(e, "noise_"), rtol=0, atol=1e-15)
        np.testing.assert_allclose(result, values(e, "received_"), rtol=0, atol=1e-12)
        assert (
            model.ta_command_samples(x["command"], x["initial"]) == e["command_samples"]
        )
        max_channel = max(
            max_channel, float(np.max(abs(result - values(e, "received_"))))
        )
    files = paths + [
        root / "src/common/NROFDM.py",
        root / "src/common/NRPhaseRotation.py",
        root / "src/channel/NRChannel.py",
        root / "src/common/_validation.py",
    ]
    report = {
        "status": "passed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "matlab_version": ofdm["matlab_version"],
        "toolbox": ofdm["toolbox"],
        "ofdm_case_count": len(ofdm["cases"]),
        "demod_case_count": len(ofdm["cases"]) * 3,
        "channel_case_count": len(channel["cases"]),
        "max_wave_abs_error": max_wave,
        "max_demod_abs_error": max_demod,
        "max_symbol_phase_error_rad": max_phase,
        "max_channel_abs_error": max_channel,
        "hashes": {
            str(p.relative_to(root))
            .replace("\\", "/"): hashlib.sha256(p.read_bytes())
            .hexdigest()
            for p in files
        },
        "note": "Python comparison of actual MATLAB references; no PRNG sequence equality assumed. Native MATLAB channel models, 5G Toolbox OFDM.",
        "cases": ofdm_cases,
    }
    (output / "NROFDM_comparison.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    log.logger.info(
        "PASS %d OFDM/%d demod/%d channel cases; waveform error %.5g",
        report["ofdm_case_count"],
        report["demod_case_count"],
        report["channel_case_count"],
        max_wave,
    )
    return report


if __name__ == "__main__":
    with ExampleLogger(__file__) as run:
        compare(run)
