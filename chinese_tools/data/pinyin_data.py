import re
CHARACTER_PINYIN_ENGLISH_MAPPING = {
    "花": ["huā","flower; blossom"],
"园": ["yuán","land used for growing plants; site used for public recreation"],
"门": ["mén","gate; door; classifier for lessons, subjects, branches of technology"],
"前": ["qián","front; forward; ahead; first; top (followed by a number); former; formerly"],
"个": ["gè","universal measure word"],
"他": ["tā","he or him"],
"后": ["hòu","back; behind; rear; afterwards; after; later"],
"外": ["wài","outside; in addition; foreign; external"],
"年": ["nián","year"],
"季": ["jì","season"],
"儿": ["ér","non-syllabic diminutive suffix"],
"看": ["kàn","to see; to look at; to read; to watch; to visit; to call on; to consider; to regard as; to look after; to treat (an illness); to depend on; to feel (that); (after verb) to give it a try; Watch out! (for a danger)"],
"花园": ["huāyuán","garden"],
"大门": ["dàmén","entrance; door; gate"],
"后门": ["hòumén","the back door; fig. under the counter (indirect way for influence or pressure)"],
"好看": ["hǎokàn","good-looking; nice-looking; good (of a movie, book, TV show etc); embarrassed; humiliated"],
"公": ["gōng","public; collectively owned; common; male (animal)"],
"朵": ["duǒ","measure word for flower"],
"可": ["kě","may, can"],
"玫": ["méi","(fine jade)"],
"菊": ["jú","chrysanthemum"],
"兰": ["lán","orchid (Cymbidium goeringii); fragrant thoroughwort (Eupatorium fortunei); lily magnolia"],
"公园": ["gōngyuán","park (for public recreation)"],
"可爱": ["kěài","adorable; cute; lovely"],
"玫瑰": ["méiguī","rugosa rose (shrub) (Rosa rugosa); rose flower"],
"菊花": ["júhuā","chrysanthemum"],
"兰花": ["lánhuā","cymbidium; orchid"],
"目前": ["mùqián","at the present time; currently"],
"个人": ["gèrén","individual; personal; oneself"],
"其他": ["qítā","other; (sth or sb) else; the rest"],
"之后": ["zhīhòu","afterwards; following; later; after"],
"另外": ["lìngwài","additional; in addition; besides; separate; other; moreover; furthermore"],
"外国": ["wàiguó","foreign (country)"],
"季节": ["jìjié","time; season; period"],
"儿子": ["érzi","son"],
"女儿": ["nǚér","daughter"],
"看来": ["kànlái","apparently; it seems that"],
"看见": ["kànjiàn","to see; to catch sight of"],
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
