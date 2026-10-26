"""对真实MATLAB输入重算SRS接收指标，保存数值误差和逐用户RI/TPMI/时延结果。"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np

from cell import NRCell
from common import NRUplinkCodebook
from diagnostics import ExampleLogger
from srs import NRSRS, NRSRSReceiver


def compare(log: ExampleLogger) -> dict:
    """任一对比失败即抛错；成功时保存同级NRSRSReceiver_comparison.json。"""
    output = Path(__file__).resolve().parent
    root = output.parents[1]
    reference_path = output/"NRSRSReceiver_reference.json"
    reference = json.loads(reference_path.read_text(encoding="utf-8-sig"))
    details = []
    max_cir_error = max_channel_error = max_noise_error = 0.0
    measurement_errors = {name:0.0 for name in ("snr_db","rssi","rssi_db","rsrp","rsrp_db","rssi_per_rx","rsrp_per_rx")}
    for case_id, case in enumerate(reference["cases"]):
        x, target = case["input"], case["expected"]
        cell = NRCell(**x["cell"])
        resources, betas = {}, {}
        configs = x["resources"] if isinstance(x["resources"], list) else [x["resources"]]
        for config in configs:
            cfg = config.copy()
            uid, beta = cfg.pop("uid"), cfg.pop("beta")
            resources[uid] = NRSRS(cell, **cfg)
            betas[uid] = beta
        rx = (np.asarray(x["rx_real"])+1j*np.asarray(x["rx_imag"])).reshape(cell.n_rx_antennas,cell.symbols_per_slot,cell.n_subcarriers)
        mask = np.asarray(x["noise_mask"],dtype=bool).reshape(rx.shape[1:]) if x["explicit_noise_mask"] else None
        result = NRSRSReceiver(cell,x["n_delay_taps"]).estimate(rx,resources,betas=betas,noise_mask=mask)
        np.testing.assert_allclose(result["noise"]["wideband_noise_power_per_rx"],target["wide_per_rx"],rtol=1e-7,atol=1e-10)
        expected_noise = np.asarray(target["narrow_per_rx"],dtype=float).reshape(cell.n_rx_antennas,cell.n_size_grid)
        actual_noise = result["noise"]["narrowband_noise_power_per_rx"]
        np.testing.assert_allclose(actual_noise,expected_noise,rtol=1e-7,atol=1e-10,equal_nan=True)
        max_noise_error = max(max_noise_error,float(np.nanmax(np.abs(actual_noise-expected_noise))))
        targets = target["users"] if isinstance(target["users"],list) else [target["users"]]
        for expected in targets:
            user = result["users"][expected["uid"]]
            cir = np.asarray(expected["cir_real"])+1j*np.asarray(expected["cir_imag"])
            channel = np.asarray(expected["channel_real"])+1j*np.asarray(expected["channel_imag"])
            np.testing.assert_allclose(user["cir"].ravel(),cir,rtol=1e-6,atol=2e-7)
            np.testing.assert_allclose(user["channel"].ravel(),channel,rtol=1e-6,atol=2e-7)
            assert (user["ri"],user["tpmi"],user["delay_samples"]) == (expected["ri"],expected["tpmi"],expected["delay_samples"])
            assert user["first_path_delay_samples"] == expected["first_path_delay_samples"]
            for metric in ("snr_db","rssi","rssi_db","rsrp","rsrp_db","rssi_per_rx","rsrp_per_rx"):
                np.testing.assert_allclose(user[metric],expected[metric],rtol=1e-6,atol=2e-6)
                measurement_errors[metric]=max(measurement_errors[metric],float(np.max(abs(np.asarray(user[metric])-expected[metric]))))
            cir_error = float(np.max(abs(user["cir"].ravel()-cir)))
            channel_error = float(np.max(abs(user["channel"].ravel()-channel)))
            max_cir_error = max(max_cir_error,cir_error)
            max_channel_error = max(max_channel_error,channel_error)
            details.append({"case_id":case_id,"user":expected["uid"],"ri":user["ri"],"tpmi":user["tpmi"],
                            "delay_samples":user["delay_samples"],"max_cir_abs_error":cir_error,"max_channel_abs_error":channel_error})
    codebook_path = root/"examples/common/NRUplinkCodebook_reference.json"
    codebooks = json.loads(codebook_path.read_text(encoding="utf-8-sig"))
    for case in codebooks["cases"]:
        w = NRUplinkCodebook.matrix(case["n_ports"],case["rank"],case["tpmi"])
        target = (np.asarray(case["real"])+1j*np.asarray(case["imag"])).reshape(w.shape)
        np.testing.assert_allclose(w,target,rtol=0,atol=1e-15)
    report = {"status":"passed","generated_at":datetime.now(timezone.utc).isoformat(),
              "matlab_version":reference["matlab_version"],"toolbox":reference["toolbox"],
              "receiver_case_count":len(reference["cases"]),"user_case_count":len(details),
              "codebook_matrix_count":len(codebooks["cases"]),"decision_or_delay_mismatches":0,
              "max_measurement_abs_errors":measurement_errors,
              "max_cir_abs_error":max_cir_error,"max_channel_abs_error":max_channel_error,
              "max_narrowband_noise_abs_error":max_noise_error,
              "hashes":{str(path.relative_to(root)).replace('\\','/'):hashlib.sha256(path.read_bytes()).hexdigest()
                        for path in [reference_path,codebook_path,root/"src/srs/NRSRSReceiver.py",
                                     root/"src/common/NRUplinkCodebook.py",root/"src/common/_uplink_tables.py"]},
              "note":"Python comparison of actual independent MATLAB vectors; full tests also check existing SRS vectors, LS condition, counts, signal and MI score.",
              "cases":details}
    (output/"NRSRSReceiver_comparison.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    log.logger.info("PASS %d receiver cases / %d user cases / %d matrices; max CIR error %.5g",
                    report["receiver_case_count"],report["user_case_count"],report["codebook_matrix_count"],max_cir_error)
    return report


if __name__ == "__main__":
    with ExampleLogger(__file__) as run:
        compare(run)
