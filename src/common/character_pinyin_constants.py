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
    "长期": ["chángqī", "long term; long time; long range (of a forecast)"],
    "多长": ["duōcháng", "how long;how much time"],
    "写下来": ["xiěxiàlái", "write down"],
    "文字": ["wénzì", "character; script; writing; written language; writing style; phraseology; CL:個|个[ge4]"],
    "名字": ["míngzì", "name (of a person or thing); CL:個|个[ge4]"],
    "它们": ["tāmen", "they (for inanimate objects)"],
    "最后": ["zuìhòu", "final; last; finally; ultimate"],
    "最近": ["zuìjìn", "recent; recently; these days; latest; soon; nearest (of locations); shortest (of routes)"],
    "连忙": ["liánmáng", "promptly; at once"],
    "帮忙": ["bāngmáng", "to help; to lend a hand; to do a favor; to do a good turn"],
    "急忙": ["jímáng", "hastily"],
    "上海": ["shànghǎi", "Shanghai municipality, central east China, abbr. to 滬|沪[Hu4]"],
    "身上": ["shēnshang", "on the body; at hand; among"],
    "晚上": ["wǎnshang", "evening; night; CL:個|个[ge4]; in the evening"],
    "上午": ["shàngwǔ", "morning; CL:個|个[ge4]"],
    "中国": ["zhōngguó", "China"],
    "其中": ["qízhōng", "among; in; included among these"],
    "下面": ["xiàmian", "down;below;underneath"],
    "一下": ["yīxià", "(used after a verb) give it a go; to do (sth for a bit to give it a try); one time; once; in a while; all of a sudden; all at once"],
    "左边": ["zuǒbiān", "left; the left side; to the left of"],
    "左面": ["zuǒmiàn", "left side"],
    "右边": ["yòubiān", "right side; right, to the right"],
    "右面": ["yòumiàn", "right side"],
    "左右": ["zuǒyòu", "left and right; nearby; approximately; attendant; to control; to influence"],
    "起来": ["qǐlái", "get up; (after a verb) indicating the beginning and continuation of an action or a state; indicating an upward movement (e.g. after 站[zhan4]); bringing things together (e.g. after 收拾[shou1 shi5]); (after a perception verb, e.g. 看[kan4]) expressing preliminary judgment; also pr. [qi3 lai5]"],
    "下来": ["xiàlái", "to come down; (after verb of motion, indicates motion down and towards us, also fig.); (indicates continuation from the past towards us); to be harvested (of crops); to be over (of a period of time); to go among the masses (said of leaders)"],
    "来到": ["láidào", "to come; to arrive"],
    "去年": ["qùnián", "last year"],
    "下去": ["xiàqù", "to go down; to descend; to go on; to continue; (of a servant) to withdraw"],
    "过去": ["guòqù", "in the past"],
    "失去": ["shīqù", "to lose"],
    "出现": ["chūxiàn", "to appear; to arise; to emerge; to show up"],
    "发出": ["fāchū", "to issue (an order, decree etc); to send out; to dispatch; to produce (a sound); to let out (a laugh)"],
    "进入": ["jìnrù", "to enter; to join; to go into"],
    "收入": ["shōurù", "to take in; income; revenue; CL:筆|笔[bi3],個|个[ge4]"],
    "乘坐": ["chéngzuò", "to ride (in a vehicle)"],
    "建立": ["jiànlì", "to establish; to set up; to found"],
    "立即": ["lìjí", "immediately"],
    "成立": ["chénglì", "to establish; to set up; to be tenable; to hold water"],
    "走向": ["zǒuxiàng", "to move towards; to head for"],
    "日": ["rì", "sun"],
    "月": ["yuè", "moon"],
    "山": ["shān", "mountain"],
    "石": ["shí", "rock"],
    "土": ["tǔ", "earth"],
    "田": ["tián", "field"],
    "水": ["shuǐ", "water"],
    "火": ["huǒ", "fire"],
    "木": ["mù", "tree"],
    "禾": ["hé", "cereal"],
    "日月": ["rìyuè", "the sun and moon"],
    "一月": ["yīyuè", "January"],
    "二月": ["èryuè", "February"],
    "十二月二十四日": ["shíèryuèèrshísìrì", "24th Dec"],
    "石山": ["shíshān", "rocky mountain"],
    "大山": ["dàshān", "big mountain"],
    "土山": ["tǔshān", "mud mountain"],
    "火山": ["huǒshān", "volcano"],
    "山水": ["shānshuǐ", "landscape;nature scene"],
    "水田": ["shuǐtián", "paddy field"],
    "石头": ["shítou", "stone"],
    "小石头": ["xiǎoshítou", "little stone"],
    "木头": ["mùtou", "wood"],
    "多长时间": ["duōchángshíjiān", "how long;how much time"],
    "半个小时": ["bàngèxiǎoshí", "half an hour"],
    "附近": ["fùjìn", "nearby"],
    "常常": ["chángcháng", "often"],
    "这里": ["zhèlǐ", "here"],
    "日子": ["rìzǐ", "day"],
    "土地": ["tǔdì", "earth and land"],
    "火车": ["huǒchē", "train"],
    "到": ["dào", "to (a place)"],
    "旅行": ["lǚxíng", "to travel"],
    "当时": ["dāngshí", "at that time"],
    "假装": ["jiǎzhuāng", "to feign"],
    "太阳": ["tàiyang", "sun"],
    "日本": ["rìběn", "Japan"],
    "月亮": ["yuèliang", "the moon"],
    "一月一日": ["yīyuèyīrì", "01/01"],
    "一座山": ["yīzuòshān", "one mountain"],
    "石头": ["shítou", "stone"],
    "一块石头": ["yīkuàishítou", "one stone"],
    "石油": ["shíyóu", "oil"],
    "农田": ["nóngtián", "farmland"],
    "水平": ["shuǐpíng", "level (of achievement etc)"],
    "树木": ["shùmù", "trees"],
    "我": ["wǒ", "I"],
    "有": ["yǒu", "to have"],
    "左": ["zuǒ", "left"],
    "来": ["lái", "to come"],
    "右": ["yòu", "right (-hand)"],
    "个": ["gè", "measure word"],
    "指": ["zhǐ", "finger"],
    "人": ["rén", "man"],
    "头": ["tóu", "head;suffix for nouns"],
    "目": ["mù", "eye"],
    "口": ["kǒu", "mouth"],
    "耳": ["ěr", "ear"],
    "手": ["shǒu", "hand"],
    "足": ["zú", "foot"],
    "大": ["dà", "big"],
    "小": ["xiǎo", "small"],
    "多": ["duō", "many"],
    "少": ["shǎo", "few"],
    "一人": ["yīrén", "one person;alone"],
    "五口人": ["wǔkǒurén", "five family members"],
    "人人": ["rénrén", "everyone"],
    "人头": ["réntóu", "human head"],
    "小手": ["xiǎoshǒu", "small hand"],
    "大人": ["dàrén", "adult"],
    "大小": ["dàxiǎo", "size"],
    "多少": ["duōshǎo", "how much"],
    "人多": ["rénduō", "many people"],
    "人少": ["rénshǎo", "few people"],
    "手指": ["shǒuzhǐ", "finger"],
    "几个": ["jǐgè", "a few"],
    "不能": ["bùnéng", "cannot"],
    "太冷了": ["tàilěngle", "too cold"],
    "可以": ["kěyǐ", "can"],
    "春节": ["chūnjié", "Spring Festival (Chinese New Year)"],
    "颜色": ["yánsè", "color"],
    "餐馆": ["cānguǎn", "restaurant"],
    "这里": ["zhèlǐ", "here"],
    "附近": ["fùjìn", "nearby"],
    "常常": ["chángcháng", "often"],
    "英文": ["yīngwén", "English (language)"],
    "汽车": ["qìchē", "car"],
    "数字": ["shùzì", "numeral"],
    "只": ["zhǐ", "classifier for birds and certain animals, one of a pair, some utensils, vessels etc"],
    "双": ["shuāng", "double"],
    "眼睛": ["yǎnjing", "eye"],
    "嘴巴": ["zuǐba", "mouth"],
    "耳朵": ["ěrduo", "ear"],
    "脚": ["jiǎo", "foot"],
    "人手": ["rénshǒu", "manpower"],
    "个人": ["gèrén", "individual"],
    "大家": ["dàjiā", "everyone"],
    "大学": ["dàxué", "university"],
    "小时": ["xiǎoshí", "hour"],
    "小孩": ["xiǎohái", "child"],
    "许多": ["xǔduō", "many"],
    "减少": ["jiǎnshǎo", "to lessen"],
    "小学": ["xiǎoxué", "elementary school"],
    "鼻子": ["bízi", "nose"],
    "脸": ["liǎn", "face"],
    "手指头": ["shǒuzhǐtou", "fingertip"],
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
