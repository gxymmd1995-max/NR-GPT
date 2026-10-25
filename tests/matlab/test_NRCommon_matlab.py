"""公共接口直接比对 MATLAB nrPRBS 比特及现有 nrSRS 的 u/v。"""

import json
from pathlib import Path

import numpy as np
import pytest

from cell import NRCell
from common import NRCommon

ROOT = Path(__file__).resolve().parents[2]


def _reference(relative, request):
    path = ROOT / relative
    if not path.exists():
        message = f"Missing actual MATLAB reference: {relative}"
        if request.config.getoption("--require-matlab"):
            pytest.fail(message)
        pytest.skip(message)
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    assert data["matlab_version"] and data["toolbox"]
    return data


@pytest.mark.matlab
def test_matlab_gold_bits(request):
    reference = _reference("examples/common/NRCommon_reference.json", request)
    assert len(reference["cases"]) == 20
    for case in reference["cases"]:
        actual = NRCommon.gold_sequence(**case["input"])
        np.testing.assert_array_equal(actual, np.asarray(case["bits"], dtype=np.uint8).reshape(-1))


@pytest.mark.matlab
def test_matlab_srs_uv_common_interface(request):
    reference = _reference("examples/srs/NRSRS_reference.json", request)
    for case in reference["cases"]:
        config, expected = case["input"], case["expected"]
        if not expected["active"]:
            continue
        cell = NRCell(**config["cell"])
        uv = NRCommon.srs_sequence_uv(config["sequence_id"], cell.n_slot,
            cell.symbols_per_slot-1-config["start_position"], config["n_symbols"],
            expected["sequence_length"], config["group_seq_hopping"], cell.symbols_per_slot)
        np.testing.assert_array_equal(uv["u"], np.atleast_1d(expected["seq_group"]))
        np.testing.assert_array_equal(uv["v"], np.atleast_1d(expected["n_seq"]))
