import re
CHARACTER_PINYIN_ENGLISH_MAPPING = {
    "上": ["", ""],
    "中": ["", "middle;center"],
    "下": ["", ""],
    "左": ["", ""],
    "右": ["", ""],
    "来": ["", ""],
    "去": ["", ""],
    "出": ["", ""],
    "入": ["", ""],
    "坐": ["", ""],
    "立": ["", ""],
    "走": ["", ""],
    "山上": ["", "on the mountain"],
    "山下": ["", "down the mountain"],
    "上头": ["shang4 tou", "above"],
    "下头": ["xia4 tou", "below;down;beneath"],
    "手中": ["", "in the hand"],
    "口中": ["", "in the mouth"],
    "左手": ["", ""],
    "右手": ["", ""],
    "左耳": ["", "left ear"],
    "右耳": ["", "right ear"],
    "上下": ["", "up and down"],
    "上上下下": ["", "ups and downs;left and right;everywhere"],
    "一上一下": ["", "one up and one down"],
    "一左一右": ["", "one left and one right"],
    "坐下": ["", ""],
    "走来": ["", "come (towards speaker)"],
    "走去": ["", ""],
    "走出去": ["", "walk out"],
    "长": ["", "long"],
    "写": ["", ""],
    "字": ["", ""],
    "它": ["", ""],
    "最": ["", ""],
    "忙": ["", ""],
    "嘴巴": ["zui3 ba", "mouth"],
    "身子": ["shen1 zi", ""],
    "写字": ["", ""],
    "普通": ["", ""],
    "少数": ["", ""],
    "了不起": ["liao3 bu4 qi3", ""],
    "赶": ["", "to overtake; to catch up with; o hurry; to rush; to try to catch (the bus etc)"],
    "培训班": ["", "training class"],
}


####################################################
####################################################
######### DO NOT TOUCH THE CODE BELOW! #########################
####################################################
####################################################
####################################################
PinyinToneMark = {
    0: "aoeiuv\u00fc",
    1: "\u0101\u014d\u0113\u012b\u016b\u01d6\u01d6",
    2: "\u00e1\u00f3\u00e9\u00ed\u00fa\u01d8\u01d8",
    3: "\u01ce\u01d2\u011b\u01d0\u01d4\u01da\u01da",
    4: "\u00e0\u00f2\u00e8\u00ec\u00f9\u01dc\u01dc",
}


def decode_pinyin(s):
    s = s.lower()
    r = ""
    t = ""
    for c in s:
        if c >= 'a' and c <= 'z':
            t += c
        elif c == ':':
            assert t[-1] == 'u'
            t = t[:-1] + "\u00fc"
        else:
            if c >= '0' and c <= '5':
                tone = int(c) % 5
                if tone != 0:
                    m = re.search("[aoeiuv\u00fc]+", t)
                    if m is None:
                        t += c
                    elif len(m.group(0)) == 1:
                        pos = PinyinToneMark[0].index(m.group(0))
                        t = t[:m.start(
                            0)] + PinyinToneMark[tone][pos] + t[m.end(0):]
                    else:
                        if 'a' in t:
                            t = t.replace("a", PinyinToneMark[tone][0])
                        elif 'o' in t:
                            t = t.replace("o", PinyinToneMark[tone][1])
                        elif 'e' in t:
                            t = t.replace("e", PinyinToneMark[tone][2])
                        elif t.endswith("ui"):
                            t = t.replace("i", PinyinToneMark[tone][3])
                        elif t.endswith("iu"):
                            t = t.replace("u", PinyinToneMark[tone][4])
                        else:
                            t += "!"
            r += t
            t = ""
    r += t
    return r
