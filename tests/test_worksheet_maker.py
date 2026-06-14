"""Tests for the worksheet (practice-card) generator."""
import os

from chinese_tools.cards import worksheet_maker as wm


def test_parse_entries_extracts_han_and_overrides():
    entries = wm.parse_entries("学习 重(zhòng) 行(hang2)")
    chars = [c for c, _ in entries]
    assert chars == ["学", "习", "重", "行"]
    overrides = {c: o for c, o in entries if o}
    assert overrides == {"重": "zhòng", "行": "hang2"}


def test_parse_entries_ignores_non_han():
    assert wm.parse_entries("a1 b2 -- 你 好!") == [("你", None), ("好", None)]


def test_resolve_pinyin_override_wins_over_default():
    # 重 most-common reading is zhòng; an override forces chóng.
    assert wm.resolve_pinyin("重", "chóng") == "chóng"
    # numbered overrides are converted to tone marks
    assert wm.resolve_pinyin("行", "hang2") == "háng"


def test_build_pdf(tmp_path):
    entries = wm.parse_entries("学习重")
    prefix = os.path.join(tmp_path, "cards")
    pdf, pages = wm.build(entries, prefix, wm.Config())
    assert os.path.exists(pdf)
    assert pages == 2  # 3 characters, 2 big cards per page


def test_build_grid_layout(tmp_path):
    entries = wm.parse_entries("花园门前个他")
    prefix = os.path.join(tmp_path, "grid")
    pdf, pages = wm.build(entries, prefix, wm.Config(layout="grid"))
    assert os.path.exists(pdf)
    assert pages == 1
