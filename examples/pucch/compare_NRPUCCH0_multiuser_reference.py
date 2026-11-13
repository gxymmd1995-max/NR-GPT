"""真实MATLAB多用户时域叠加、候选复相关和分用户检测比较；不使用发送真值选择候选。"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np

from cell import NRCell
from channel import NRChannel
from diagnostics import ExampleLogger
from pucch import NRPUCCH0, NRPUCCH0Transmitter, NRPUCCH0Receiver


def compare(logger=None, write_report=True):
    """逐用户对实际MATLAB混合波形解码，全部断言通过才写JSON报告。"""
    output = Path(__file__).resolve().parent
    root = output.parents[1]
    path = output / "NRPUCCH0_multiuser_reference.json"
    reference = json.loads(path.read_text(encoding="utf-8-sig"))
    assert reference["matlab_version"] and reference["toolbox"]
    max_mixed = max_received = max_correlation = max_metric = 0.0
    details = []
    for case_index, case in enumerate(reference["cases"]):
        x, e = case["input"], case["expected"]
        cell = NRCell(**x["cell"])
        model = NRChannel(cell)
        gains = np.array(x["gain_real"]) + 1j * np.array(x["gain_imag"])
        receivers = {}
        mixed = np.zeros((2, e["n_samples"]), complex)
        for user in range(3):
            uid = f"UE{user}"
            resource = NRPUCCH0(
                cell,
                prb=0,
                start_symbol=8,
                n_symbols=2,
                second_hop_prb=3,
                initial_cyclic_shift=x["initial_shifts"][user],
                hopping_id=731,
                group_hopping="enable",
            )
            receivers[uid] = NRPUCCH0Receiver(
                resource, 1, False, x["carrier_frequency_hz"], x["detection_threshold"]
            )
            tx = NRPUCCH0Transmitter(resource, x["carrier_frequency_hz"]).transmit(
                [x["harq_ack"][user]]
            )["waveform"]
            spatial = gains[:, user, None] * model.timing_advance(tx, 2)
            if not x["active"][user]:
                spatial[:] = 0
            mixed += model.frequency_offset(
                model.timing_advance(spatial, -5), 731, 0.23
            )
        allocation = NRPUCCH0Receiver.validate_cyclic_shift_group(receivers)

        def wave(prefix):
            return (
                np.array(e[prefix + "real"]) + 1j * np.array(e[prefix + "imag"])
            ).reshape(2, e["n_samples"])

        expected_mixed = wave("mixed_")
        expected_received = wave("received_")
        standard = (
            np.array(x["standard_real"]) + 1j * np.array(x["standard_imag"])
        ).reshape(mixed.shape)
        received, _ = model.add_awgn(mixed, x["snr_db"], noise_standard=standard)
        np.testing.assert_allclose(mixed, expected_mixed, atol=2e-9, rtol=0)
        np.testing.assert_allclose(received, expected_received, atol=2e-9, rtol=0)
        max_mixed = max(max_mixed, float(np.max(abs(mixed - expected_mixed))))
        max_received = max(
            max_received, float(np.max(abs(received - expected_received)))
        )
        for target in e["users"]:
            uid = target["uid"]
            r = receivers[uid].receive(
                expected_received,
                known_frequency_offset_hz=731,
                known_initial_phase_rad=0.23,
                known_delay_samples=3,
                cp_fraction=0.5,
            )
            assert r["detected"] == target["detected"]
            user_index = int(uid[-1])
            assert r["detected"] == bool(x["active"][user_index])
            assert r["harq_ack"] == (
                [x["harq_ack"][user_index]] if x["active"][user_index] else None
            )
            assert r["harq_ack"] == (
                [target["best_bit"]] if target["detected"] else None
            )
            corr = np.array(target["correlation_real"]) + 1j * np.array(
                target["correlation_imag"]
            )
            # 约3.5GHz载频的逐符号相位在两实现间存在约4e-9 rad浮点差；单位增益相关值保留此相位。
            np.testing.assert_allclose(
                r["candidate_correlation_symbols"].ravel(), corr, atol=1e-8, rtol=0
            )
            np.testing.assert_allclose(
                [c["metric"] for c in r["candidates"]],
                target["metrics"],
                atol=2e-9,
                rtol=0,
            )
            max_correlation = max(
                max_correlation,
                float(np.max(abs(r["candidate_correlation_symbols"].ravel() - corr))),
            )
            max_metric = max(max_metric, abs(r["metric"] - target["metric"]))
            details.append(
                {
                    "case": case_index,
                    "uid": uid,
                    "detected": r["detected"],
                    "harq_ack": r["harq_ack"],
                    "metric": r["metric"],
                    "candidate_shift_set": allocation[uid],
                }
            )
    files = [
        path,
        output / "export_NRPUCCH0_multiuser_reference.m",
        output / "compare_NRPUCCH0_multiuser_reference.py",
        root / "src/pucch/NRPUCCH0.py",
        root / "src/pucch/NRPUCCH0Transmitter.py",
        root / "src/pucch/NRPUCCH0Receiver.py",
        root / "src/common/NRCommon.py",
        root / "src/common/_low_papr_tables.py",
        root / "src/common/NROFDM.py",
        root / "src/common/NRPhaseRotation.py",
        root / "src/channel/NRChannel.py",
    ]
    report = {
        "status": "passed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "matlab_version": reference["matlab_version"],
        "toolbox": reference["toolbox"],
        "case_count": len(reference["cases"]),
        "user_result_count": len(details),
        "decision_mismatch_count": 0,
        "max_mixed_abs_error": max_mixed,
        "max_received_abs_error": max_received,
        "max_correlation_abs_error": max_correlation,
        "max_metric_abs_error": max_metric,
        "hashes": {
            str(p.relative_to(root))
            .replace("\\", "/"): hashlib.sha256(p.read_bytes())
            .hexdigest()
            for p in files
        },
        "cases": details,
    }
    if write_report:
        (output / "NRPUCCH0_multiuser_comparison.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
    if logger is not None:
        logger.info(
            "PASS %d actual MATLAB cases / %d user results",
            report["case_count"],
            len(details),
        )
    return report


if __name__ == "__main__":
    with ExampleLogger(__file__) as run:
        compare(run.logger)
