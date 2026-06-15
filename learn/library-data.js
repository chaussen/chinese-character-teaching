/* library-data.js — 学写字 · Character Studio · the Library (added book series).
   Everything on the Home screen is grouped by SERIES → BOOK → lesson → character.
   This file holds the *added* series (beyond the school's own four-book series,
   which lives in app-data.js, and the General theme library in general-data.js).

   Structure:
     series[]            a publisher / course (e.g. 暨南大学《中文》)
       .id .cn .cnpy .en .sub          how the section is labelled on Home
       .books[]          the volumes in that series
         .id             unique id (used for progress keys — keep stable!)
         .title .cn .cnpy .vol         the volume's name + "第一册" style label
         .glyph .pigment .accent…      the card's colour identity
         .lessons[]      { n, title, chars:[Hanzi…] }

   ▸ HOUSE RULE: only list a character whose stroke data is already bundled
     (in app-data.js or general-data.js → CHAR_INDEX). The engine drops & logs any
     it can't resolve, so a missing character never breaks a lesson. Characters MAY
     repeat across books — that's fine: stroke data + enrichment are shared by Hanzi
     (one source of truth), while progress is tracked per book (id:char).

   This pilot seeds 暨南大学《中文》第一册. 99 of its 144 characters are bundled today;
   the remaining 45 are listed in the handoff, ready to drop in. */
window.LIBRARY_DATA = {
  series: [
    {
      id: "ZW",
      cn: "中文",
      cnpy: [["中", "zhōng"], ["文", "wén"]],
      en: "Zhōngwén · Jinan University",
      sub: "暨南大学《中文》 — the worldwide overseas-Chinese course",
      books: [
        {
          id: "ZW1",
          title: "Zhōngwén Book 1",
          cn: "中文",
          cnpy: [["中", "zhōng"], ["文", "wén"]],
          vol: "第一册",
          glyph: "文",
          pigment: "Jade",
          accent: "#4C7A52", accentSoft: "#CBE0CD", tint: "#EAF2EA",
          lessons: [
            { n: 1,  title: "数字 · Numbers",        chars: ["一","二","三","四","五","六","七","八","九","十","百","千"] },
            { n: 2,  title: "身体 · My body",         chars: ["人","头","目","耳","口","牙","心","手","足","大","小","多","少"] },
            { n: 3,  title: "上下 · Here & there",    chars: ["上","下","左","右","中","来","去","走"] },
            { n: 4,  title: "天地 · Sky & earth",     chars: ["日","月","天","东","南","西","北","子","女"] },
            { n: 5,  title: "自然 · Nature",          chars: ["风","云","雨","山","石","田","木","水","火","土"] },
            { n: 6,  title: "动物 · Animals & food",  chars: ["马","牛","羊","鸟","虫","鱼","米","门","果"] },
            { n: 7,  title: "认识你 · About me",      chars: ["学","家","好","我","今","年","是","文"] },
            { n: 8,  title: "家人 · My family",       chars: ["有","爸","妈","哥","姐","妹","和","爱"] },
            { n: 9,  title: "上学 · At school",       chars: ["校","了","高","说","早","同","你"] },
            { n: 10, title: "方向 · Which way",       chars: ["认","起","前","后"] },
            { n: 11, title: "四季 · The seasons",     chars: ["春","夏","秋","冬","花","树","黄","雪","飞"] },
            { n: 12, title: "天气 · Warm & cold",     chars: ["热","身"] }
          ]
        }
      ]
    }
  ]
};
