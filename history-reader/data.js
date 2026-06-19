/* 史案 — 史书知识图谱阅读器 · data layer (window.SHI_DATA)
 *
 * This is the *shape* the production system must generalise (see the design
 * handoff). Two principles are baked into the structure on purpose:
 *
 *   1. Sourced data is the product. Every ENTITIES record carries provenance
 *      (`src`) and cross-references (`seen`). These are the trust contract —
 *      the UI marks any entity WITHOUT a `src` as 未溯源 (unverified) rather
 *      than silently presenting it as fact.
 *
 *   2. One passage today, the whole canon tomorrow. Nothing here assumes a
 *      single hardcoded text: ENTITIES is a *global registry* keyed by a
 *      canonical id, and PASSAGES is a collection whose lines reference the
 *      registry by id («entityId» knowledge layer · ⟨langId⟩ language layer).
 *      A marker may carry a surface override — «id|高祖» / ⟨id|surface⟩ — so one
 *      entity (canonical 梁武帝) can appear under different names across texts
 *      (高祖 here) while still resolving to the same id. Entities dedupe across
 *      passages (their `seen` aggregates every text they appear in); language
 *      tokens are per-context, so each mention gets its own id.
 *      A real build replaces these literals with an API-backed store and a
 *      cross-text (互见) engine; the rendering engine should not need to change.
 */
(function () {
  // ── category metadata (知识层 / 專名) — colour + underline texture ──
  // Texture lets a category stay distinguishable even with colour off.
  const CATS = {
    person: { label: '人物', color: '#B23A2B', deco: 'solid' },
    place:  { label: '地名', color: '#2C7A70', deco: 'wavy' },
    office: { label: '官职', color: '#3F6B8C', deco: 'double' },
    era:    { label: '年号', color: '#B26B00', deco: 'dotted' },
    rank:   { label: '爵位', color: '#6C5AA6', deco: 'dashed' }
  };

  // ── grammar-role colours (语言层) — dashed underline in all cases ──
  const LANG_ROLES = {
    '句式': '#B23A2B',
    '副词': '#3F6B8C',
    '活用': '#B0772A',
    '代词': '#6C5AA6',
    '介词': '#2C7A70'
  };

  // ── global entity registry ──
  // id → { w, cat, brief, fields:[{k,v}], src, seen:[chapter…] }
  // The `今比` field, when present, is the 现代类比 (modern-analogy) anchor the
  // detail dock leads with. `src` is MANDATORY for a verified entity.
  const ENTITIES = {
    shuofang: {
      w: '朔方', cat: 'place', brief: '今内蒙古杭锦旗一带',
      fields: [
        { k: '今地', v: '今内蒙古杭锦旗、磴口一带' },
        { k: '沿革', v: '汉武帝元朔二年（前127）置朔方郡，为北边军镇重地' },
        { k: '辨', v: '本传两说并存——「朔方人，或云雁门人」，籍贯本不确定' }
      ],
      src: '《读史方舆纪要》卷61', seen: ['梁书·武帝纪', '南史·侯景传']
    },
    yanmen: {
      w: '雁門', cat: 'place', brief: '今山西代县一带',
      fields: [
        { k: '今地', v: '今山西忻州代县' },
        { k: '形胜', v: '雁门关所在，历代北疆第一要塞' }
      ],
      src: '《元和郡县图志》河东道', seen: ['南史·侯景传']
    },
    zhenbing: {
      w: '北鎮戍兵', cat: 'office', brief: '北魏六镇的边防戍卒',
      fields: [
        { k: '性质', v: '北魏沿边六镇（沃野、怀朔、武川等）的戍防军士' },
        { k: '处境', v: '六镇本为拱卫旧都的精锐；孝文迁都洛阳后地位骤降、待遇沉沦，终酿「六镇之乱」' },
        { k: '今比', v: '边防戍卒 · 起于行伍的最底层' }
      ],
      src: '《魏书·官氏志》·六镇考', seen: ['魏书·广阳王深传', '北史·尔朱荣传']
    },
    gerong: {
      w: '葛榮', cat: 'person', brief: '北魏六镇起义军领袖',
      fields: [
        { k: '身份', v: '六镇之乱后期起义军首领，自称天子，国号齐' },
        { k: '结局', v: '528年滏口之战为尔朱荣所擒杀' },
        { k: '关系', v: '侯景随尔朱荣讨平葛荣，以此战之功受擢——是其发迹的起点' }
      ],
      src: '《魏书·卷九八·葛荣传》', seen: ['北史·尔朱荣传', '资治通鉴·梁纪']
    },
    erzhurong: {
      w: '爾朱榮', cat: 'person', brief: '北魏权臣 · 天柱大将军 · 493–530',
      fields: [
        { k: '生卒', v: '493–530' },
        { k: '身份', v: '北魏末契胡军阀，官至天柱大将军，一度执掌朝政' },
        { k: '大事', v: '河阴之变（沉杀太后及朝臣两千余人）、平定葛荣' },
        { k: '关系', v: '侯景归附的第一位重要军阀，其军旅生涯由此起步' }
      ],
      src: '《魏书·卷七四·尔朱荣传》', seen: ['北史·尔朱荣传', '梁书·侯景传', '资治通鉴·梁纪']
    },
    dingzhou: {
      w: '定州刺史', cat: 'office', brief: '定州（今河北定州）最高长官',
      fields: [
        { k: '辖区', v: '定州，治今河北定州' },
        { k: '职权', v: '州级最高长官，常加都督、行台衔，军政一把抓' },
        { k: '品级', v: '约正三品（北魏制）' },
        { k: '今比', v: '省长兼省军区主官' }
      ],
      src: '《通典·职官·州牧刺史》', seen: ['魏书·地形志']
    },
    daxingtai: {
      w: '大行臺', cat: 'office', brief: '总揽一方军政的中央派出长官',
      fields: [
        { k: '性质', v: '「行台」为尚书台派往地方、总领数州军政的最高机构，「大行台」为其长官' },
        { k: '职权', v: '集军、政、财于一身，权倾一方' },
        { k: '今比', v: '战区 + 大区行政首长' }
      ],
      src: '《通典·职官·行台省》', seen: ['北齐书·神武纪']
    },
    puyang: {
      w: '濮陽郡公', cat: 'rank', brief: '郡公爵 · 封地濮阳',
      fields: [
        { k: '爵等', v: '郡公——位在县公之上、郡王之下' },
        { k: '封地', v: '濮阳郡，今河南濮阳一带' },
        { k: '意味', v: '由戍卒至开国郡公，可见其骤贵之速' }
      ],
      src: '《隋书·百官志》·爵制', seen: []
    },
    gaohuan: {
      w: '高歡', cat: 'person', brief: '东魏权臣 · 北齐奠基者 · 496–547',
      fields: [
        { k: '生卒', v: '496–547，谥神武皇帝' },
        { k: '身份', v: '东魏实际掌权者，北齐高氏王朝奠基人' },
        { k: '大事', v: '灭尔朱氏、立东魏、与西魏宇文泰长期对峙' },
        { k: '关系', v: '侯景转投高欢，受任专制河南；高欢一死，侯景即叛' }
      ],
      src: '《北齐书·卷一·神武纪》', seen: ['魏书·孝静帝纪', '梁书·侯景传', '南史·贼臣传']
    },
    henan: {
      w: '河南', cat: 'place', brief: '黄河以南诸州 · 侯景拥兵之地',
      fields: [
        { k: '范围', v: '此处指黄河以南、东魏所辖十三州之地' },
        { k: '战略', v: '介于东魏、西魏、南梁之间，是侯景拥兵自重、待价而沽的本钱' }
      ],
      src: '《资治通鉴·梁纪十六》', seen: ['梁书·武帝纪', '南史·侯景传']
    },
    wuding5: {
      w: '武定五年', cat: 'era', brief: '公元547年 · 东魏孝静帝',
      fields: [
        { k: '公元', v: '547年' },
        { k: '在位', v: '东魏孝静帝元善见，实权在高欢、高澄父子' },
        { k: '大事', v: '是年高欢卒；侯景举河南叛东魏，先降西魏复降南梁——乱局之始' }
      ],
      src: '《魏书·孝静帝纪》武定五年', seen: ['梁书·武帝纪', '资治通鉴·梁纪']
    },
    liangwu: {
      w: '梁武帝', cat: 'person', brief: '南朝梁开国皇帝萧衍 · 464–549',
      fields: [
        { k: '生卒', v: '464–549' },
        { k: '在位', v: '502–549，南梁开国之君' },
        { k: '大事', v: '崇佛，四度舍身同泰寺；晚年纳侯景，终致「侯景之乱」，饿死台城' },
        { k: '关系', v: '接纳侯景来降、封河南王，埋下侯景之乱的祸根' }
      ],
      src: '《梁书·卷三·武帝纪下》', seen: ['南史·梁本纪', '梁书·侯景传', '梁書·韋叡傳', '梁書·曹景宗傳']
    },
    henanwang: {
      w: '河南王', cat: 'rank', brief: '梁武帝封侯景的王爵',
      fields: [
        { k: '爵等', v: '王爵——异姓封王，殊礼' },
        { k: '用意', v: '梁武帝以高爵招纳，冀不战而收河南之地' }
      ],
      src: '《梁书·武帝纪》太清元年', seen: ['南史·侯景传']
    },
    dajiangjun: {
      w: '大將軍', cat: 'office', brief: '武官最高品级之一',
      fields: [
        { k: '品级', v: '一品重号将军，武职之极' },
        { k: '性质', v: '多为荣宠、统兵之号' }
      ],
      src: '《通典·职官·武官》', seen: []
    },

    // ── 钟离之战 (天监五年/506) — 《梁书·韦叡传》卷12 + 《梁书·曹景宗传》卷9 ──
    weirui: {
      w: '韋叡', cat: 'person', brief: '南朝梁名将 · 字怀文 · 442–520',
      fields: [
        { k: '生卒', v: '442–520，谥严，京兆杜陵人（叡，亦作睿）' },
        { k: '身份', v: '南朝梁名将，钟离之战大破北魏，魏人惮之，号「韦虎」' },
        { k: '用兵', v: '持重多谋；临阵乘素木舆、执白角如意指挥，从容不乱' },
        { k: '关系', v: '钟离之役受曹景宗节度，二将相得，遂成大捷' }
      ],
      src: '《梁书·卷十二·韦叡传》', seen: ['梁書·曹景宗傳', '南史·韋叡傳', '資治通鑑·梁紀']
    },
    caojingzong: {
      w: '曹景宗', cat: 'person', brief: '南朝梁名将 · 字子震 · 457–508',
      fields: [
        { k: '生卒', v: '457–508（天监七年卒，年五十二），新野人' },
        { k: '身份', v: '梁初名将，钟离之战都督众军二十万，与韦叡破魏' },
        { k: '性情', v: '任侠尚气、好驰猎；钟离欲专其功而违诏冒进，幸未败' },
        { k: '关系', v: '韦叡受其节度；高祖戒以「二将和，师必济」' }
      ],
      src: '《梁书·卷九·曹景宗传》', seen: ['梁書·韋叡傳', '南史·曹景宗傳', '資治通鑑·梁紀']
    },
    yuanying: {
      w: '元英', cat: 'person', brief: '北魏宗室名将 · 中山王 · ?–510',
      fields: [
        { k: '身份', v: '北魏宗室，南安王拓跋桢之子，封中山王，宣武朝名将' },
        { k: '大事', v: '天监五年率众围钟离，号百万；邵阳洲一败，仅以身免' },
        { k: '别名', v: '本姓拓跋，《梁书》或作「托跋英」「拓跋英」' },
        { k: '关系', v: '钟离之战的北魏主帅，为韦叡、曹景宗所破' }
      ],
      src: '《魏书·卷十九下·景穆十二王下》（元英）', seen: ['梁書·韋叡傳', '梁書·曹景宗傳', '魏書·景穆十二王傳', '資治通鑑·梁紀']
    },
    changyizhi: {
      w: '昌義之', cat: 'person', brief: '梁将 · 钟离守将 · 历阳乌江人',
      fields: [
        { k: '身份', v: '梁北徐州刺史，天监五年困守钟离' },
        { k: '事迹', v: '以数千之众拒魏号百万，城坚不下，卒待援破敌' },
        { k: '关系', v: '韦叡、曹景宗驰援所救之将' }
      ],
      src: '《梁书·卷十八·昌义之传》', seen: ['梁書·韋叡傳', '梁書·曹景宗傳', '南史·昌義之傳']
    },
    fengdaogen: {
      w: '馮道根', cat: 'person', brief: '梁将 · 字巨基 · 钟离水军主将',
      fields: [
        { k: '身份', v: '梁初宿将，钟离之战为韦叡水军主力' },
        { k: '事迹', v: '率斗舰焚魏邵阳洲浮桥，身自搏战，魏军遂溃' }
      ],
      src: '《梁书·卷十八·冯道根传》', seen: ['梁書·韋叡傳', '南史·馮道根傳']
    },

    duling: {
      w: '京兆杜陵', cat: 'place', brief: '今陕西西安东南 · 韦氏郡望',
      fields: [
        { k: '今地', v: '今陕西省西安市东南（汉宣帝杜陵一带）' },
        { k: '族望', v: '京兆韦氏自汉丞相韦贤以来，世为三辅著姓' }
      ],
      src: '《元和郡县图志·关内道》·京兆', seen: ['梁書·韋叡傳', '南史·韋叡傳']
    },
    hefei: {
      w: '合肥', cat: 'place', brief: '今安徽合肥 · 韦叡赴援出发地',
      fields: [
        { k: '今地', v: '今安徽省合肥市' },
        { k: '战略', v: '江淮间重镇；韦叡自合肥径道驰援钟离' }
      ],
      src: '《读史方舆纪要》庐州府·合肥', seen: ['梁書·韋叡傳', '資治通鑑·梁紀']
    },
    zhongli: {
      w: '鐘離', cat: 'place', brief: '今安徽凤阳东北 · 淮南要塞',
      fields: [
        { k: '今地', v: '今安徽省滁州市凤阳县东北临淮关一带' },
        { k: '形胜', v: '淮河南岸要塞，南北争夺的桥头堡' },
        { k: '大事', v: '天监五年（506）钟离之战，梁军于此大破北魏元英' }
      ],
      src: '《读史方舆纪要》凤阳府·临淮（钟离）', seen: ['梁書·韋叡傳', '梁書·曹景宗傳', '梁書·昌義之傳', '資治通鑑·梁紀']
    },
    shaoyangzhou: {
      w: '邵陽洲', cat: 'place', brief: '钟离城外淮中沙洲 · 决战之地',
      fields: [
        { k: '位置', v: '钟离城外淮水中的沙洲' },
        { k: '大事', v: '魏军两岸架桥跨淮；韦叡以火船焚桥、水军决战于此' }
      ],
      src: '《资治通鉴·梁纪五》天监五年', seen: ['梁書·韋叡傳', '梁書·曹景宗傳', '資治通鑑·梁紀']
    },
    xinye: {
      w: '新野', cat: 'place', brief: '今河南新野 · 曹景宗籍贯',
      fields: [
        { k: '今地', v: '今河南省南阳市新野县' },
        { k: '沿革', v: '南阳属县；南朝雍州地域豪族多出于此' }
      ],
      src: '《元和郡县图志》邓州·新野', seen: ['梁書·曹景宗傳']
    },
    daorenzhou: {
      w: '道人洲', cat: 'place', brief: '钟离附近淮中洲渚',
      fields: [
        { k: '位置', v: '钟离左近淮水中的沙洲' },
        { k: '本段', v: '高祖诏景宗顿兵道人洲，待众军齐进而后发' }
      ],
      src: '《资治通鉴·梁纪五》天监五年', seen: ['梁書·曹景宗傳', '資治通鑑·梁紀']
    },

    duduzhongjun: {
      w: '都督衆軍', cat: 'office', brief: '出征时总统诸路军马的统帅',
      fields: [
        { k: '性质', v: '战时临时最高军职，节制各州刺史、诸将' },
        { k: '本段', v: '曹景宗都督众军二十万拒魏，韦叡受其节度' },
        { k: '今比', v: '战区联合作战司令' }
      ],
      src: '《通典·职官·都督》', seen: ['梁書·曹景宗傳', '梁書·韋叡傳']
    },
    yuzhoucishi: {
      w: '豫州刺史', cat: 'office', brief: '豫州最高军政长官',
      fields: [
        { k: '辖区', v: '豫州（南朝侨置，治近江淮）' },
        { k: '职权', v: '州级军政长官，常领兵；韦叡时领豫州之众赴援' },
        { k: '今比', v: '省长兼省军区主官' }
      ],
      src: '《通典·职官·州牧刺史》', seen: ['梁書·韋叡傳']
    },
    zhengbei: {
      w: '征北將軍', cat: 'office', brief: '高级征伐武职 · 四征将军之一',
      fields: [
        { k: '品级', v: '四征将军之一，位高，主一方征伐' },
        { k: '本段', v: '曹景宗以征北将军都督众军' }
      ],
      src: '《通典·职官·武官》四征将军', seen: ['梁書·曹景宗傳']
    },

    tianjian5: {
      w: '天監五年', cat: 'era', brief: '公元506年 · 梁武帝天监五年',
      fields: [
        { k: '公元', v: '506年' },
        { k: '在位', v: '梁武帝萧衍天监年间' },
        { k: '大事', v: '钟离之战，梁大破北魏，南朝难得之大捷' }
      ],
      src: '《梁书·武帝纪》天监五年', seen: ['梁書·韋叡傳', '梁書·曹景宗傳', '梁書·武帝紀']
    }
  };

  // ── language-layer tokens — context-specific reading (NOT the whole entry) ──
  const LANG = {
    jian:   { w: '見', role: '句式', sub: '被动',   roleFull: '被动标志',   gloss: '助动词，表被动，相当于「被」。「見憚鄉里」＝被乡里所忌惮。', src: '王力《古代汉语》·被动句' },
    shao:   { w: '稍', role: '副词', sub: '古义',   roleFull: '时间副词',   gloss: '古义为「渐渐、逐渐」，非今义「稍微」。「稍立功效」＝渐渐立下功劳。', src: '《古汉语常用字字典》' },
    zhuang: { w: '壯', role: '活用', sub: '意动',   roleFull: '意动用法',   gloss: '形容词意动：「以……为壮」，即赏识、看重。「甚壯之」＝很赏识他。', src: '王力《古代汉语》·词类活用' },
    qi:     { w: '器', role: '活用', sub: '名作动', roleFull: '名词作动词', gloss: '名词「器（才具）」用作动词：器重、看重。「器其才」＝看重他的才能。', src: '《古汉语常用字字典》' },
    zhi1:   { w: '之', role: '代词', sub: '第三人称', roleFull: '人称代词', gloss: '第三人称代词，作宾语，指代侯景。「壯之」＝赏识他。', src: '《古汉语虚词词典》' },
    zhi2:   { w: '之', role: '代词', sub: '第三人称', roleFull: '人称代词', gloss: '第三人称代词，指代侯景来降一事。「納之」＝接纳了他。', src: '《古汉语虚词词典》' },
    yi:     { w: '以', role: '介词', sub: '凭借/率', roleFull: '介词',      gloss: '介词，「率领、带着」。「以眾降歡」＝率部众投降高欢。', src: '《古汉语虚词词典》' },

    // ── 韦叡传 语言层 ──
    w_bi:   { w: '比', role: '副词', sub: '古义',     roleFull: '时间副词',     gloss: '古义「等到、及至」，非「比较」。「比曉而營立」＝等到天亮，营垒已立成。', src: '《古汉语常用字字典》·比' },
    w_yi:   { w: '以', role: '介词', sub: '工具',     roleFull: '介词',         gloss: '介词「用、拿」。「灌之以膏」＝用油脂浇灌（其上）。', src: '《古汉语虚词词典》·以' },
    w_he:   { w: '何', role: '句式', sub: '感叹',     roleFull: '感叹/疑问句',  gloss: '「是何神也」＝这是何等神奇啊！「何」为疑问代词作谓语，「……也」收以感叹。', src: '王力《古代汉语》·句式' },
    w_qi:   { w: '其', role: '代词', sub: '第三人称', roleFull: '人称代词',     gloss: '第三人称代词，指韦叡（军）。「英甚憚其強」＝元英很忌惮他（军）的强劲。', src: '《古汉语虚词词典》·其' },

    // ── 曹景宗传 语言层 ──
    c_gu:    { w: '固', role: '副词', sub: '坚决',     roleFull: '语气副词',     gloss: '副词「坚决地、再三地」。「景宗固啓」＝景宗再三启奏（请战）。', src: '《古汉语常用字字典》·固' },
    c_zu:    { w: '卒', role: '副词', sub: '通「猝」', roleFull: '副词（通假）', gloss: '通「猝」，突然、忽然。「暴風卒起」＝狂风骤然刮起。', src: '《古汉语常用字字典》·卒' },
    c_suoyi: { w: '所以', role: '句式', sub: '固定结构', roleFull: '「所以」结构', gloss: '「所以」＝用来……的（凭借、缘由）。「此所以破賊也」＝这正是用以破贼的凭借。', src: '王力《古代汉语》·所以' },
    c_gai:   { w: '蓋', role: '副词', sub: '推测',     roleFull: '语气副词',     gloss: '句首副词，表推测「大概、想必」。「蓋天意乎」＝大概是天意吧。', src: '《古汉语虚词词典》·盖' },
    c_yan:   { w: '焉', role: '代词', sub: '兼词',     roleFull: '兼词',         gloss: '兼词，相当于「于此」。「亦預焉」＝（韦叡）也参与了此役。', src: '《古汉语虚词词典》·焉' }
  };

  // ── passages collection (one shipped; engine must not assume one) ──
  // `lines` reference the registry inline: «entityId» knowledge · ⟨langId⟩ language.
  // map / rel / rise describe the 传主 and belong to the passage. In production
  // they would be assembled cross-text (互見法) from many mentions.
  const PASSAGES = [{
    id: 'houjing-liangshu',
    title: '梁書·侯景傳',
    sub: '节选 · 唐 · 姚思廉 撰',
    seal: '侯',
    subject: '侯景',
    intro: '侯景本北镇戍卒，乘六镇之乱而起，辗转事尔朱荣、高欢，终以河南之地降梁复叛，酿成「侯景之乱」，南朝由是衰落。本段叙其出身与早年发迹之路。',
    lines: [
      '侯景，字萬景，«shuofang»人，或云«yanmen»人。少而不羈，⟨jian⟩憚鄉里。',
      '及長，驍勇有膂力，善騎射，以選為«zhenbing»，⟨shao⟩立功效。',
      '後與«gerong»戰，敗之，遂從«erzhurong»為先鋒。榮甚⟨zhuang⟩⟨zhi1⟩，擢為«dingzhou»、«daxingtai»，封«puyang»。',
      '及«gaohuan»誅爾朱氏，景⟨yi⟩眾降歡，仍為定州刺史。歡⟨qi⟩其才，授以兵柄，使擁眾十萬，專制«henan»。',
      '«wuding5»，歡卒，景懼禍，遂以河南十三州來降。«liangwu»納⟨zhi2⟩，封«henanwang»、«dajiangjun»，使持節。'
    ],

    // 地理视图 · 行迹。ll = [经度, 纬度] 县级真实坐标；底图(geo.js)按经纬度投影。
    // alt:true = 学界存疑的地点。route = 按时序连线的点 id。
    map: {
      caption: '侯景行迹 · 北朝中后期 · 县级经纬度底图（黄河/淮河/长江 + 今省界）',
      points: [
        { id: 'shuofang', order: 1, ll: [107.15, 39.83], mod: '今内蒙古杭锦旗', note: '籍贯 · 起点（一说雁门）' },
        { id: 'yanmen',   order: 1, ll: [112.96, 39.07], mod: '今山西代县',     note: '一说籍贯 · 学界存疑', alt: true },
        { id: 'dingzhou', order: 2, ll: [114.99, 38.52], mod: '今河北定州',     note: '528 擢定州刺史' },
        { id: 'henan',    order: 3, ll: [114.30, 34.40], mod: '黄河以南十三州',  note: '530s 专制河南 · 拥众十万' },
        { id: 'jiankang', order: 4, ll: [118.79, 32.06], mod: '今江苏南京',     note: '547 举河南降梁所向 · 后陷台城', ref: 'liangwu' }
      ],
      route: ['shuofang', 'dingzhou', 'henan', 'jiankang']
    },

    // 人物关系视图 · 以传主为中心。xy = 节点示意坐标。
    rel: {
      center: { w: '侯景', sub: '本传主' },
      nodes: [
        { id: 'gerong',    w: '葛榮',   rel: '敌',     sub: '破之，以功受擢', xy: [20, 22] },
        { id: 'erzhurong', w: '爾朱榮', rel: '归附',   sub: '第一位军阀主公', xy: [80, 20] },
        { id: 'gaohuan',   w: '高歡',   rel: '归附→叛', sub: '授兵柄，旋叛',   xy: [82, 74] },
        { id: 'liangwu',   w: '梁武帝', rel: '降',     sub: '纳降，封河南王', xy: [18, 76] }
      ]
    },

    // 升迁 / 时间轴。rank = 官位高低(0–100)，时间轴的纵轴高度。ref = 关联专名。
    rise: [
      { year: '525',  tag: '起步', rank: 34, title: '北鎮戍兵',                ref: 'zhenbing', note: '以选为北镇戍卒，稍立功效——起于行伍最底层。' },
      { year: '528',  tag: '骤升', rank: 82, title: '定州刺史 · 大行臺 · 濮陽郡公', ref: 'dingzhou', note: '从尔朱荣讨平葛荣，以功一跃为州刺史、开国郡公。' },
      { year: '530s', tag: '高位', rank: 96, title: '專制河南 · 擁眾十萬',        ref: 'henan',    note: '转投高欢，受任专制河南，拥兵十万，俨然一方之雄。' },
      { year: '547',  tag: '转折', rank: 62, title: '舉河南來降',              ref: 'wuding5',  note: '高欢卒，景惧祸而叛；先降西魏，复以十三州降梁，封河南王。' },
      { year: '549',  tag: '后事', rank: 46, title: '陷臺城',                  ref: 'liangwu',  note: '侯景之乱爆发，梁武帝饿死台城，南朝盛极而衰。' }
    ]
  },

  {
    id: 'weirui-liangshu',
    title: '梁書·韋叡傳',
    sub: '节选 · 钟离之战 · 唐 · 姚思廉 撰',
    seal: '韋',
    subject: '韋叡',
    intro: '韋叡，南朝梁名将，京兆杜陵人。天监五年（506），北魏中山王元英以号称百万之众围钟离，韦叡自合肥驰援，夜筑营垒、以火船焚淮桥，大破魏军，为南朝罕见的大捷。本段叙其钟离用兵。',
    lines: [
      '韋叡，字懷文，«duling|京兆杜陵»人也。',
      '«tianjian5|五年»，魏中山王«yuanying|元英»寇北徐州，圍刺史«changyizhi|昌義之»於«zhongli|鐘離»，衆號百萬，連城四十餘。',
      '«liangwu|高祖»遣«zhengbei|征北將軍»«caojingzong|曹景宗»，都督衆軍二十萬以拒之。次«shaoyangzhou|邵陽洲»，築壘相守，«liangwu|高祖»詔叡率«yuzhoucishi|豫州»之衆會焉。',
      '叡自«hefei|合肥»逕道由陰陵大澤行，值澗穀，輒飛橋以濟。',
      '叡曰：「«zhongli|鐘離»今鑿穴而處，負戶而汲，車馳卒奔，猶恐其後，而況緩乎！魏人已墮吾腹中，卿曹勿憂也。」',
      '旬日而至«shaoyangzhou|邵陽»。初，«liangwu|高祖»敕景宗曰：「韋叡，卿之鄉望，宜善敬之。」',
      '«caojingzong|景宗»見叡，禮甚謹。«liangwu|高祖»聞之，曰：「二將和，師必濟矣。」',
      '叡於«caojingzong|景宗»營前二十里，夜掘長塹，樹鹿角，截洲爲城，⟨w_bi⟩曉而營立。',
      '«yuanying|元英»大驚，以杖擊地曰：「是⟨w_he⟩神也！」',
      '明旦，«yuanying|英»自率衆來戰，叡乘素木輿，執白角如意麾軍，一日數合，英甚憚⟨w_qi⟩強。',
      '魏人先於«shaoyangzhou|邵陽洲»兩岸爲兩橋，樹柵數百步，跨淮通道。',
      '叡裝大艦，使梁郡太守«fengdaogen|馮道根»、廬江太守裴邃、秦郡太守李文釗等爲水軍。',
      '以小船載草，灌之⟨w_yi⟩膏，從而焚其橋。',
      '而«fengdaogen|道根»等皆身自搏戰，軍人奮勇，呼聲動天地，無不一當百，魏人大潰。',
      '«yuanying|元英»見橋絕，脫身遁去。'
    ],
    map: {
      caption: '韋叡赴援钟离行迹 · 天监五年(506) · 县级经纬度底图（钟离在淮河之滨）',
      points: [
        { id: 'duling',       order: 1, ll: [109.00, 34.18], mod: '今陕西西安东南',   note: '京兆杜陵 · 韦氏郡望、起点' },
        { id: 'hefei',        order: 2, ll: [117.28, 31.86], mod: '今安徽合肥',       note: '自合肥径道驰援' },
        { id: 'zhongli',      order: 3, ll: [117.62, 32.95], mod: '今安徽凤阳东北',   note: '钟离之战 · 解围' },
        { id: 'shaoyangzhou', order: 3, ll: [117.72, 32.99], mod: '钟离城外淮中沙洲', note: '邵阳洲 · 火船焚桥决战' }
      ],
      route: ['duling', 'hefei', 'zhongli']
    },
    rel: {
      center: { w: '韋叡', sub: '本传主' },
      nodes: [
        { id: 'yuanying',    w: '元英',   rel: '敌',       sub: '邵阳洲大破之',   xy: [80, 22] },
        { id: 'caojingzong', w: '曹景宗', rel: '友军·主将', sub: '二将和，师必济', xy: [20, 20] },
        { id: 'changyizhi',  w: '昌義之', rel: '救援',     sub: '困守钟离，叡往救', xy: [22, 78] },
        { id: 'liangwu',     w: '梁武帝', rel: '君主',     sub: '高祖诏叡赴援',   xy: [80, 78] }
      ]
    }
  },

  {
    id: 'caojingzong-liangshu',
    title: '梁書·曹景宗傳',
    sub: '节选 · 钟离之战 · 唐 · 姚思廉 撰',
    seal: '曹',
    subject: '曹景宗',
    intro: '曹景宗，南朝梁名将，新野人。天监五年钟离之战，他都督众军二十万救昌义之，与豫州刺史韦叡协力破魏。本段记其受命赴援、欲专战功而违诏冒进的曲折，及高祖「二将和，师必济」之识。',
    lines: [
      '曹景宗，字子震，«xinye|新野»人也。父欣之，爲宋將，位至征虜將軍、徐州刺史。',
      '«tianjian5|五年»，魏«yuanying|托跋英»寇«zhongli|鐘離»，圍徐州刺史«changyizhi|昌義之»。',
      '«liangwu|高祖»詔景宗督衆軍援義之，«yuzhoucishi|豫州刺史»«weirui|韋叡»亦預⟨c_yan⟩，而受景宗節度。',
      '詔景宗頓«daorenzhou|道人洲»，待衆軍齊集俱進。',
      '景宗⟨c_gu⟩啓，求先據«shaoyangzhou|邵陽洲»尾，«liangwu|高祖»不聽。',
      '景宗欲專其功，乃違詔而進，值暴風⟨c_zu⟩起，頗有渰溺，復還守先頓。',
      '«liangwu|高祖»聞之，曰：「此⟨c_suoyi⟩破賊也。景宗不進，⟨c_gai⟩天意乎！',
      '若孤軍獨往，城不時立，必見狼狽。今得待衆軍同進，始大捷矣。」'
    ],
    map: {
      caption: '曹景宗钟离之役行迹 · 天监五年(506) · 县级经纬度底图（淮上诸洲）',
      points: [
        { id: 'xinye',      order: 1, ll: [112.36, 32.52], mod: '今河南新野',     note: '籍贯 · 新野将门' },
        { id: 'zhongli',    order: 2, ll: [117.62, 32.95], mod: '今安徽凤阳东北', note: '都督众军援钟离' },
        { id: 'daorenzhou', order: 2, ll: [117.85, 33.02], mod: '钟离左近淮中洲', note: '顿兵道人洲，待众军齐进' }
      ],
      route: ['xinye', 'zhongli']
    },
    rel: {
      center: { w: '曹景宗', sub: '本传主' },
      nodes: [
        { id: 'yuanying',   w: '元英',   rel: '敌',       sub: '钟离对垒，破之',   xy: [80, 22] },
        { id: 'weirui',     w: '韋叡',   rel: '部属·节度', sub: '韦叡受景宗节度',   xy: [20, 20] },
        { id: 'changyizhi', w: '昌義之', rel: '救援',     sub: '受围钟离，往援',   xy: [22, 78] },
        { id: 'liangwu',    w: '梁武帝', rel: '君主',     sub: '高祖诏督众军',     xy: [80, 78] }
      ]
    }
  }];

  window.SHI_DATA = { CATS, LANG_ROLES, ENTITIES, LANG, PASSAGES };
})();
