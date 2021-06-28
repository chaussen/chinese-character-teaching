import re
CHARACTER_PINYIN_ENGLISH_MAPPING = {
    "向": ["", "direction; orientation; to face; to turn toward; to; towards; "],
    "用": ["", "to use; to employ; to have to; to eat or drink; "],
    "关系": ["guan1 xi", "relationship"],
    "舒服": ["shu1 fu", "comfortable; feeling well"],
    "痛苦": ["", "pain; suffering; painful; CL:個|个[ge4]"],
    "会": ["hui4", "be capable of"],
    "给": ["", "to supply; to provide"],
    "起来": ["", "(after a verb) indicating the beginning and continuation of an action or a state; indicating an upward movement (e.g. after 站[zhan4]); bringing things together (e.g. after 收拾[shou1 shi5]); (after a perception verb, e.g. 看[kan4]) expressing preliminary judgment; also pr. [qi3 lai5]"],
    "家": ["", "home; family; (polite) my (sister, uncle etc); classifier for families or businesses; refers to the philosophical schools of pre-Han China; noun suffix for a specialist in some activity, such as a musician or revolutionary, corresponding to English -ist, -er, -ary or -ian; CL:個|个[ge4]"],
    "她": ["", "she"],
    "你": ["", "you (informal, as opposed to courteous 您[nin2])"],
    "就": ["", "at once; right away; only; just (emphasis); as early as; already; as soon as; then; in that case; as many as; even if; to approach; to move towards; to undertake; to engage in; to suffer; subjected to; to accomplish; to take advantage of; to go with (of foods); with regard to; concerning"],
    "像": ["", "to resemble; to be like; to look as if; such as; appearance; image; portrait; image under a mapping (math.)"],
    "好": ["hao3", "good"],
    "开": ["", "to open; to start; to turn on; to boil; to write out (a prescription, check, invoice etc); to operate (a vehicle)"],
    "了": ["le", "final particle"],
    "真": ["", "really; truly; indeed; real; true; genuine"],
    "高": ["", "high; tall; above average; loud; your (honorific)"],
    "兴": ["xing4", "feeling or desire to do sth; interest in sth; excitement"],
    "车": ["", "vehicle;car"],
    "见": ["jian4", "to see"],
    "说": ["", "to speak; to say; to explain; to scold; to tell off; a theory (usually in compounds such as 日心说 heliocentric theory)"],
    "早": ["", "early; morning; Good morning!; long ago; prematurely"],
    "们": ["", "plural marker for pronouns, and nouns referring to individuals"],
    "开学": ["", "foundation of a University or College; school opening; the start of a new term"],
    "高兴": ["gao1 xing4", "happy; glad; willing (to do sth); in a cheerful mood"],
    "校车": ["", "school bus"],
    "你们": ["", "you (plural)"],
    "开始": ["", "to begin; beginning; to start; initial; CL:個|个[ge4]"],
    "离开": ["", "to depart; to leave"],
    "真正": ["", "genuine; real; true; genuinely"],
    "认真": ["", "conscientious; earnest; serious; to take seriously; to take to heart"],
    "提高": ["", "to raise; to increase; to improve"],
    "兴趣": ["xing4 qu4", "interest (desire to know about sth); interest (thing in which one is interested); hobby; CL:個|个[ge4]"],
    "汽车": ["", "car; automobile; bus; CL:輛|辆[liang4]"],
    "意见": ["", "idea; opinion; suggestion; objection; complaint; CL:點|点[dian3],條|条[tiao2]"],
    "看见": ["", "to see; to catch sight of"],
    "说明": ["", "to explain; to illustrate; to indicate; to show; to prove; explanation; directions; caption; CL:個|个[ge4]"],
    "小说": ["", "novel; fiction; CL:本[ben3],部[bu4]"],
    "人们": ["", "people"],
    "良好": ["", "good; favorable; well; fine"],
}

############################################
####################################################
# DO NOT TOUCH THE CODE BELOW! #############
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
