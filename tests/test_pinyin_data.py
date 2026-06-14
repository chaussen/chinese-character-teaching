"""Tests for pinyin data helpers."""
from chinese_tools.data.pinyin_data import decode_pinyin


def test_decode_numbered_pinyin():
    assert decode_pinyin("zhong4") == "zhòng"
    assert decode_pinyin("hao3") == "hǎo"
    assert decode_pinyin("ma1") == "mā"


def test_decode_handles_neutral_tone():
    assert decode_pinyin("de") == "de"
