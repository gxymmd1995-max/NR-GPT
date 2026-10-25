"""物理信道固定配色、别名归一化、未知标签与网格绘图分类。"""

import re

import numpy as np
import pytest

from grid import CHANNEL_COLORS, UNKNOWN_COLOR, channel_color, encode_owners


def test_palette_is_unique_immutable_and_hex():
    assert len(set(CHANNEL_COLORS.values())) == len(CHANNEL_COLORS)
    assert UNKNOWN_COLOR not in CHANNEL_COLORS.values()
    assert all(re.fullmatch(r"#[0-9A-F]{6}", value) for value in CHANNEL_COLORS.values())
    assert {"SSB", "PDSCH", "PDCCH", "PUSCH", "PUCCH", "PRACH", "SRS"} <= CHANNEL_COLORS.keys()
    with pytest.raises(TypeError):
        CHANNEL_COLORS["PDSCH"] = "#000000"


@pytest.mark.parametrize("owner,label", [
    ("", "FREE"), ("  ", "FREE"), (" pdsch ", "PDSCH"), ("PDSCH:UE0", "PDSCH"),
    ("pdsch:ue1", "PDSCH"), ("DM-RS", "DMRS"), ("PT-RS", "PTRS"),
    ("CSI-RS", "CSI_RS"), ("SS/PBCH", "SSB"), ("ss-pbch", "SSB"),
])
def test_aliases_and_owner_suffix(owner, label):
    assert channel_color(owner) == CHANNEL_COLORS[label]


@pytest.mark.parametrize("owner", [None, True, 1])
def test_bad_owner_type(owner):
    with pytest.raises(TypeError):
        channel_color(owner)


def test_unknown_is_visible_and_order_independent():
    assert channel_color("future_channel") == UNKNOWN_COLOR
    assert channel_color("future_channel") != channel_color("")
    assert channel_color(":UE0") == UNKNOWN_COLOR  # 非空未知标签不能误显示为空闲。
    a = np.array([["PDSCH:UE0", "SSB", ""], ["mystery_z", "DM-RS", "mystery_a"]])
    before = a.copy()
    codes, labels, colors = encode_owners(a)
    assert labels == ("FREE", "SSB", "PDSCH", "DMRS", "MYSTERY_A", "MYSTERY_Z")
    assert colors[-2:] == (UNKNOWN_COLOR, UNKNOWN_COLOR)
    np.testing.assert_array_equal(np.asarray(labels)[codes], [["PDSCH", "SSB", "FREE"], ["MYSTERY_Z", "DMRS", "MYSTERY_A"]])
    np.testing.assert_array_equal(a, before)
    _, reversed_labels, reversed_colors = encode_owners(a[:, ::-1])
    assert (reversed_labels, reversed_colors) == (labels, colors)


def test_three_dimensional_and_single_category():
    owners = np.full((2, 3, 4), "PUSCH:UE0")
    codes, labels, colors = encode_owners(owners)
    assert codes.shape == owners.shape
    assert not np.any(codes)
    assert labels == ("PUSCH",)
    assert colors == (CHANNEL_COLORS["PUSCH"],)


@pytest.mark.parametrize("owners,error", [
    (np.array("SSB"), ValueError), (np.array(["SSB"]), ValueError),
    (np.empty((0, 3), dtype="U1"), ValueError), (np.zeros((2, 3)), TypeError),
    (np.full((2, 3), "SSB", dtype=object), TypeError),
])
def test_invalid_owner_arrays(owners, error):
    with pytest.raises(error):
        encode_owners(owners)
