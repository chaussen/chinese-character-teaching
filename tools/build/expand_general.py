#!/usr/bin/env python3
"""Expand learn/general-data.js with the full common-character pool.

Every character that already carries stroke data in the app (app-data.js,
general-data.js, library-chars.js) — and therefore already has a recording in
audio/char — is grouped by theme and appended to the General library. The
existing 10 themed groups are preserved untouched; new themed groups are added
below them. No network access and NO new audio are required: each added char
is drawn from the existing stroke/audio pool.

Run:  python3 tools/build/expand_general.py
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEARN = ROOT / "learn"


def load_window(path):
    text = path.read_text(encoding="utf-8")
    m = re.search(r"window\.\w+\s*=\s*", text)
    body = text[m.end():].rstrip().rstrip(";").rstrip()
    return json.loads(body)


# ---- master stroke-data index: ch -> {ch,py,en,s,m,strokes} -----------------
def build_index():
    idx = {}

    def take(rec):
        ch = rec.get("ch")
        if not ch or ch in idx:
            return
        if "s" not in rec or "m" not in rec:
            return
        idx[ch] = {
            "ch": ch,
            "py": rec.get("py", ""),
            "en": rec.get("en", ""),
            "s": rec["s"],
            "m": rec["m"],
            "strokes": rec.get("strokes", len(rec["s"])),
        }

    gen = load_window(LEARN / "general-data.js")
    for g in gen["groups"]:
        for c in g["chars"]:
            take(c)
    app = load_window(LEARN / "app-data.js")
    for band in app.get("bands", []):
        for unit in band.get("units", []):
            for c in unit.get("chars", []):
                take(c)
    lib = load_window(LEARN / "library-chars.js")
    for c in lib.get("chars", []):
        take(c)
    return gen, idx


# ---- new themed groups (every char drawn from the existing pool) ------------
# Titles follow the existing "中文 · English" style. Each char appears once;
# any pool char not listed here is swept into the final catch-all group.
NEW_THEMES = [
    ("学习读写 · Learning & writing",
     "文句章题课图片纸笔记号画读写讲练考试答复教知懂算译研究篇诗描典词本习"),
    ("说话交流 · Speaking & talking",
     "话语言问唱吟颂论评辞谎信声音歌聊闻报赞批劝聂祝称请谢喂喊叫"),
    ("心思情意 · Mind, thought & feeling",
     "想念意觉忘疑愿望梦怕惊恐喜欢乐悲苦怀志急要猜肯敢吓哭慌丧盼尊敬愤福希啼悯"),
    ("身体（更多）· More of the body",
     "脚腿嘴背脑腰肚鼻唇睛皮血脏颐颜面体发尾"),
    ("健康看病 · Health & illness",
     "病药医疼痛伤累康健死治护困饿渴"),
    ("食物饮食 · Food & eating",
     "饭菜肉米汤茶蛋饼油香甜饱烤筷勺蜜粽饺蔬瓜粮粉鲜"),
    ("穿衣打扮 · Clothes & wearing",
     "衣裙帽服装戴洗澡布穿"),
    ("房屋家居 · House & home",
     "门墙床桌椅屋房楼灯缸笼炉伞镜柱架刀庐舍"),
    ("城镇场所 · Town & places",
     "店市街城园馆院社厅殿庄廊桥陵岸区校乡"),
    ("交通出行 · Getting around",
     "车船飞路骑载舟艘汽航追赶逛旅游运道往驾行"),
    ("天气季节 · Weather & seasons",
     "雪晴暖冷阳露季气热"),
    ("山水大地 · Land & water",
     "江湖川岛沙滩泥洞瀑林流陆地景浪溅淹滴青"),
    ("植物 · Plants",
     "竹苗芽梢禾秧叶葡萄松植果"),
    ("更多动物 · More animals",
     "龙狼鼠熊狮猴猿狐鲸蚁蚂鸦乌骆驼豚鲨虾"),
    ("手上动作 · Hand actions",
     "拿打拉抓挖采摘搬挂折扫捏捉扑砍砸拔伸摇撞撒贴拍踢端举拾带钻扒捞碰缝投雕担拆提搭挑"),
    ("更多动作 · More actions",
     "跳爬冲倒躺睡靠跪歇停留守围藏取起住进落飘掉步钓弄跟居仰斗离眠归沉止出入见到垂视拜动玩回立"),
    ("做事劳动 · Doing & working",
     "做办成用造建修筑设计种养帮助营保努农锄培管创劳干活"),
    ("大小形状 · Size & shape",
     "高低长短深浅粗细尖弯圆扁凸凹宽窄矮巨硬软空满角形孔顶底反遥方"),
    ("数量单位 · Amount & measure",
     "半倍匹颗棵块条件份座位群列串尺寸元双张层数全几第顿幅些俩粒次类单量克加分秤剩"),
    ("金钱买卖 · Money & shopping",
     "钱卖买票价款银金购付富穷贵省商"),
    ("时间（更多）· More about time",
     "昨午夕晨夜期初末始终遍刚久历纪当古先刻代永迟晓岁节寿"),
    ("工作与人 · Work & people",
     "员工师官民众客友夫妻父母孩童伯邻祖侯帝皇王雄子朋亲职业司绅"),
    ("文艺体育 · Arts & sport",
     "舞演琴球赛泳武艺彩影篮牌输赢胜鼓曲"),
    ("国家社会 · Country & society",
     "国族政统法兵战华汉侨俗团"),
    ("代词疑问 · Pronouns & questions",
     "这那个它其此谁哪何怎什么各"),
    ("连词副词 · Joining & describing words",
     "就又而但却虽既仍还再更最太都才只常总必将须及比较同如该因所以被使向把从且除无然等并为能每似越够唯渐皆未别可会超者附没另连"),
    ("常用动词 · More common verbs",
     "传化解决选择认属达结关过给借验破找突定接制随透埋产禁丢灭划寻毕领束贡献侵奋抗兴集迎射升充临改参受扩励断补拒绝求切交完得任继续害照合送收通放让变欺骗察探换沿争"),
    ("常用形容词 · More describing words",
     "美漂亮聪近远净便宜奇快慢难利静清正浩辛洁丰实错勇巧轻坏准繁荣强独旧顺秘慈衰重精特暗性广显严勤私楚真新老闹专适对忙肥异"),
    ("抽象常用字 · Common abstract characters",
     "故科技网息环境史展表首系具事样理术力式程器名像德务誉杰义媒垃联功效料纲部基令玉瓷智烟牢宝英线朝间内约生电灵机珠劲衡孟品珍误亡"),
    ("语气与声音 · Particles & sounds",
     "了着吗呢吧啊呀啦乎之响"),
]


def main():
    gen, idx = build_index()

    existing = {c["ch"] for g in gen["groups"] for c in g["chars"]}
    pool = set(idx)  # everything with stroke data + (essentially) audio
    candidates = pool - existing  # chars to place into new groups
    print(f"pool={len(pool)} existing-general={len(existing)} to-add={len(candidates)}")

    placed = set()
    new_groups = []
    for title, chars in NEW_THEMES:
        members = []
        for ch in chars:
            if ch in candidates and ch not in placed:
                members.append(idx[ch])
                placed.add(ch)
        if members:
            new_groups.append({"title": title, "chars": members})

    leftovers = [ch for ch in candidates if ch not in placed]
    # keep a stable, frequency-ish order: fall back to pool insertion order
    order = {ch: i for i, ch in enumerate(idx)}
    leftovers.sort(key=lambda c: order[c])
    if leftovers:
        new_groups.append({
            "title": "常用字（更多）· More everyday characters",
            "chars": [idx[ch] for ch in leftovers],
        })
    print(f"placed={len(placed)} leftovers={len(leftovers)}")
    print("leftovers:", "".join(leftovers))

    # sanity: no char placed twice across new groups
    seen = {}
    for g in new_groups:
        for c in g["chars"]:
            seen[c["ch"]] = seen.get(c["ch"], 0) + 1
    dupes = [c for c, n in seen.items() if n > 1]
    assert not dupes, f"duplicate placements: {dupes}"

    gen["groups"].extend(new_groups)
    total = sum(len(g["chars"]) for g in gen["groups"])
    print(f"groups now={len(gen['groups'])} total chars={total}")

    header = (LEARN / "general-data.js").read_text(encoding="utf-8")
    header = header[:header.index("window.GENERAL_DATA")]
    (LEARN / "general-data.js").write_text(
        header + "window.GENERAL_DATA = "
        + json.dumps(gen, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    print("wrote learn/general-data.js")


if __name__ == "__main__":
    main()
