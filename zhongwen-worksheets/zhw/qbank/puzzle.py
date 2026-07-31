"""游戏 — puzzle and game question types. All padding characters stay in scope."""

from __future__ import annotations

from typing import List, Optional, Tuple

from ..render import Question, esc, blank
from . import register, Ctx


def _grid_html(grid: List[List[str]], highlight=None, coords: bool = True) -> str:
    hl = set(highlight or [])
    head = ""
    if coords:
        head = ("<tr><td style='border:0'></td>" +
                "".join(f"<td style='border:0;font-size:8pt;color:#888'>{c+1}</td>"
                        for c in range(len(grid[0]))) + "</tr>")
    rows = []
    for r, row in enumerate(grid):
        cells = ""
        if coords:
            cells += (f"<td style='border:0;font-size:8pt;color:#888'>"
                      f"{chr(65+r)}</td>")
        for c, ch in enumerate(row):
            style = "background:#e8e8e8;font-weight:700" if (r, c) in hl else ""
            cells += f'<td style="{style}">{esc(ch)}</td>'
        rows.append(f"<tr>{cells}</tr>")
    return f'<table class="grid-tbl">{head}{"".join(rows)}</table>'


@register("word_search", "字词搜索", "Word search", "puzzle",
          needs=("words",), default_count=6, marks_each=1, minutes_each=1.2)
def word_search(ctx: Ctx) -> Optional[Question]:
    size = ctx.p("size", 9)
    words = [w.word for w in ctx.words() if 2 <= len(w.word) <= size]
    words = ctx.pick(words, ctx.count)
    if len(words) < 3:
        return None
    grid = [[None] * size for _ in range(size)]
    placed: List[Tuple[str, List[Tuple[int, int]]]] = []
    for w in words:
        for _ in range(90):
            horiz = ctx.rng.random() < 0.5
            r = ctx.rng.randrange(size if horiz else size - len(w) + 1)
            c = ctx.rng.randrange(size - len(w) + 1 if horiz else size)
            cells = [(r, c + i) if horiz else (r + i, c) for i in range(len(w))]
            if all(grid[y][x] in (None, w[i]) for i, (y, x) in enumerate(cells)):
                for i, (y, x) in enumerate(cells):
                    grid[y][x] = w[i]
                placed.append((w, cells))
                break
    if len(placed) < 3:
        return None
    pad = [c.char for c in ctx.all_chars()] or list("一二三四五六七八九十")
    targets = [w for w, _ in placed]

    def accidental(g):
        lines = ["".join(r) for r in g]
        lines += ["".join(g[y][x] for y in range(size)) for x in range(size)]
        return sum(sum(l.count(w) for l in lines) for w in targets) > len(targets)

    blanks = [(r, c) for r in range(size) for c in range(size) if grid[r][c] is None]
    for _ in range(40):                       # re-roll padding until the key is unique
        for (r, c) in blanks:
            grid[r][c] = ctx.pick(pad, 1)[0]
        if not accidental(grid):
            break
    from ..render import wordbank
    bank = wordbank([w for w, _ in placed], "找出这些词", "Find these words")
    key_lines = "　".join(
        f'{w} ({chr(65+cells[0][0])}{cells[0][1]+1}→{chr(65+cells[-1][0])}{cells[-1][1]+1})'
        for w, cells in placed)
    hl = [cell for _, cells in placed for cell in cells]
    return Question(
        type_id="word_search", title_zh="字词搜索", title_en="Word search",
        instruction_zh="在方格里横着或竖着找出下面的词语，圈起来。",
        instruction_en="Find each word in the grid, reading across or down. Circle it.",
        body_html=bank + _grid_html(grid),
        answer_html=key_lines + "<div style='margin-top:2mm'>"
                    + _grid_html(grid, hl) + "</div>",
        student_hanzi="".join("".join(r) for r in grid),
        solution=[(w, f"{chr(65+cs[0][0])}{cs[0][1]+1}") for w, cs in placed],
        answer_mode="bijection",
        meta={"grid": grid, "targets": [w for w, _ in placed]},
        marks=len(placed), marks_each=1, items_n=len(placed),
        est_minutes=1.2 * len(placed),
    )


@register("char_maze", "汉字迷宫", "Character maze", "puzzle",
          needs=("chars",), default_count=1, marks_each=5, minutes_each=4.0)
def char_maze(ctx: Ctx) -> Optional[Question]:
    size = ctx.p("size", 7)
    bank_size = ctx.p("bank_size", 12)
    # cap the walkable set — printing 50+ "valid" characters makes every cell
    # walkable and the maze meaningless, and the bank no longer matches its
    # own label ("this lesson's characters")
    pool = ctx.chars()
    if len(pool) < 3:
        return None
    targets = [c.char for c in ctx.pick(pool, min(bank_size, len(pool)))]
    tset = set(targets)
    others = [c.char for c in ctx.all_chars() if c.char not in tset]
    if len(others) < 3:
        others = [c for c in "一二三四五六七八九十上下大小" if c not in tset]
    if len(others) < 3:
        return None                 # cannot guarantee the path is the only path
    # build a monotone right/down path
    path = [(0, 0)]
    r = c = 0
    while (r, c) != (size - 1, size - 1):
        if r == size - 1:
            c += 1
        elif c == size - 1:
            r += 1
        elif ctx.rng.random() < 0.5:
            c += 1
        else:
            r += 1
        path.append((r, c))
    pset = set(path)
    grid = [[None] * size for _ in range(size)]
    for (y, x) in path:
        grid[y][x] = ctx.pick(targets, 1)[0]
    for y in range(size):
        for x in range(size):
            if (y, x) not in pset:
                grid[y][x] = ctx.pick(others, 1)[0]
    from ..render import wordbank
    bank = wordbank(sorted(set(targets)), "可以走的字", "Characters you may step on")
    return Question(
        type_id="char_maze", title_zh="汉字迷宫", title_en="Character maze",
        instruction_zh="从左上角走到右下角，只能走上面列出的字，只能向右或向下。",
        instruction_en="Travel from top-left to bottom-right stepping only on the "
                       "characters listed above. You may move right or down only.",
        body_html=bank + _grid_html(grid, coords=True),
        answer_html=" → ".join(f"{chr(65+y)}{x+1}" for y, x in path)
                    + "<div style='margin-top:2mm'>"
                    + _grid_html(grid, path) + "</div>",
        student_hanzi="".join("".join(r) for r in grid),
        solution=[("path", " → ".join(f"{chr(65+y)}{x+1}" for y, x in path))],
        answer_mode="unique",
        marks=5, marks_each=5, items_n=1, est_minutes=4.0,
    )


@register("code_breaker", "密码句子", "Code breaker", "puzzle",
          needs=("sentences",), default_count=1, marks_each=5, minutes_each=4.0)
def code_breaker(ctx: Ctx) -> Optional[Question]:
    sents = ctx.scope.target_sentences()
    if not sents:
        return None
    s = ctx.pick(sents, 1)[0]
    chars = sorted({ch for ch in s if "\u4e00" <= ch <= "\u9fff"})
    if len(chars) < 4:
        return None
    codes = ctx.shuffled(list(range(1, len(chars) + 1)))
    key = dict(zip(chars, codes))
    legend = "".join(
        f'<td>{esc(ch)}</td>' for ch in chars)
    nums = "".join(f'<td>{key[ch]}</td>' for ch in chars)
    table = (f'<table class="pytab"><tr><th>字</th>{legend}</tr>'
             f'<tr><th>码</th>{nums}</tr></table>')
    coded = "　".join(str(key[ch]) if ch in key else ch for ch in s)
    return Question(
        type_id="code_breaker", title_zh="密码句子", title_en="Break the code",
        instruction_zh="用密码表把数字变成汉字，写出这句话。",
        instruction_en="Use the code table to turn the numbers back into characters.",
        body_html=table + f'<div style="margin:2.5mm 0;font-size:12pt;'
                          f'letter-spacing:1px">{esc(coded)}</div>'
                          f'<div class="wline"></div><div class="wline"></div>',
        answer_html=esc(s), student_hanzi=s,
        solution=[(coded, s)], answer_mode="unique",
        marks=5, marks_each=5, items_n=1, est_minutes=4.0,
    )


@register("bingo_card", "汉字宾果", "Bingo card", "puzzle",
          needs=("chars",), default_count=1, marks_each=0, minutes_each=0.0,
          confidence="open")
def bingo_card(ctx: Ctx) -> Optional[Question]:
    n = ctx.p("size", 4)
    pool = [c.char for c in ctx.all_chars()]
    if len(pool) < n * n:
        return None
    cells = ctx.pick(pool, n * n)
    grid = [cells[i * n:(i + 1) * n] for i in range(n)]
    return Question(
        type_id="bingo_card", title_zh="汉字宾果", title_en="Character bingo",
        instruction_zh="老师读一个字，找到就打勾。一行、一列或一条斜线全中就喊「宾果」。",
        instruction_en="Tick a character when the teacher calls it. A full row, "
                       "column or diagonal wins.",
        body_html=_grid_html(grid, coords=False).replace(
            'width:9mm;height:9mm', 'width:16mm;height:16mm'),
        answer_html="每张卡的字都不同，作为课堂游戏使用。 "
                    "Each generated card differs — change the seed for a new card.",
        student_hanzi="".join(cells), answer_mode="open",
        marks=0, est_minutes=0.0,
        notes="Re-run with a different seed to print a different card for each student.",
    )
