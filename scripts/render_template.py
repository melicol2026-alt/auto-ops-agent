# -*- coding: utf-8 -*-
"""图文渲染骨架：PIL 代码出图，零出图额度、文字 100% 准确。

三种封面版式（见 references/03）：
    evidence  证据窗   —— 能给证据时优先
    list      清单数字 —— 能数条数时
    compare   前后对比 —— 能前后对照时

两个必踩的坑，这里已经处理：
1. 字体缺字形：`✗` 在微软雅黑里没有字形，会渲染成方框 → 用 × 或 ASCII
2. 文本超宽：来源行、长标题超出画布 → 自动降字号循环

平台适配：只改 CANVAS。小红书 1080×1440，抖音 1080×1920，公众号 900×500。
"""

import os

from PIL import Image, ImageDraw, ImageFont

CANVAS = (1080, 1440)
M = 80                       # 页边距
FONT_DIR = "C:/Windows/Fonts"
FR, FB = "msyh.ttc", "msyhbd.ttc"

THEMES = {
    "light": {"bg": "#F7F3EC", "ink": "#1F2328", "sub": "#6B7280",
              "accent": "#E4572E", "line": "#E5E0D8", "good": "#2E7D5B", "bad": "#C0392B"},
    "dark":  {"bg": "#14161A", "ink": "#FFFFFF", "sub": "#9AA0A6",
              "accent": "#E8B84B", "line": "#2A2E35", "good": "#7BD389", "bad": "#FF6B5B"},
}


def _f(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)


def _fit(d, text, font_path, size, max_w, floor=22):
    """自动降字号，直到宽度放得下。"""
    while size > floor:
        f = _f(font_path, size)
        if d.textlength(text, font=f) <= max_w:
            return f
        size -= 2
    return _f(font_path, floor)


def _save(img, out):
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    img.save(out)
    print(f"  ✓ {out}")


# ---------------------------------------------------------------- 封面
def draw_cover(item, theme="light", out="cover.png"):
    """item 需含 cover_main / cover_sub / tag，以及版式专属字段。"""
    t = THEMES[theme]
    W, H = CANVAS
    img = Image.new("RGB", (W, H), t["bg"])
    d = ImageDraw.Draw(img)
    layout = item.get("layout", "list")

    # 顶部方向标签
    d.rectangle([M, 70, M + 8, 130], fill=t["accent"])
    d.text((M + 28, 84), item.get("tag", ""), font=_f(FR, 34), fill=t["sub"], anchor="lt")

    if layout == "evidence":
        _cover_evidence(d, item, t, W, H)
    elif layout == "compare":
        _cover_compare(d, item, t, W, H)
    else:
        _cover_list(d, item, t, W, H)

    # 底部来源行：证据必须可追溯
    src = item.get("evidence", {}).get("source") or item.get("source")
    if src:
        d.line([M, H - 116, W - M, H - 116], fill=t["line"], width=2)
        f = _fit(d, src, FR, 28, W - 2 * M, floor=20)
        d.text((M, H - 96), src, font=f, fill=t["sub"], anchor="lt")

    _save(img, out)
    return img


def _cover_evidence(d, item, t, W, H):
    """气泡放原文，红色批注放打脸事实 —— 把"我查过了"画在封面上。"""
    ev = item["evidence"]
    top = 220
    f = _fit(d, item["cover_main"], FB, 72, W - 2 * M, floor=44)
    d.text((M, top), item["cover_main"], font=f, fill=t["ink"], anchor="lt")
    top += 130

    # 气泡
    bx, by, bw, bh = M, top + 30, W - 2 * M, 300
    d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=24,
                        fill=_mix(t["bg"], t["ink"], 0.05), outline=t["line"], width=2)
    d.text((bx + 32, by + 26), ev.get("bubble_label", ""),
           font=_f(FR, 30), fill=t["sub"], anchor="lt")
    bf = _fit(d, ev.get("bubble_text", ""), FR, 42, bw - 64, floor=28)
    d.text((bx + 32, by + 84), ev.get("bubble_text", ""), font=bf, fill=t["ink"], anchor="lt")

    # 红批注（用 ×，不要用 ✗ —— 微软雅黑缺字形）
    ny = ev.get("note_line", by + bh + 40)
    nf = _fit(d, ev.get("note_text", ""), FB, 46, W - 2 * M, floor=30)
    d.text((M, ny), ev.get("note_text", ""), font=nf, fill=t["bad"], anchor="lt")

    y2 = ny + 150
    d.line([M, y2, W - M, y2], fill=t["line"], width=2)
    sf = _fit(d, item["cover_sub"], FB, 54, W - 2 * M, floor=36)
    d.text((M, y2 + 40), item["cover_sub"], font=sf, fill=t["ink"], anchor="lt")
    if ev.get("steps"):
        stf = _fit(d, ev["steps"], FR, 36, W - 2 * M, floor=26)
        d.text((M, y2 + 118), ev["steps"], font=stf, fill=t["sub"], anchor="lt")


def _cover_list(d, item, t, W, H):
    """超大数字 + 清单预览：扫一眼就知道能得到几条。"""
    li = item["list"]
    top = 230
    d.text((M, top), str(li["num"]), font=_f(FB, 200), fill=t["accent"], anchor="lt")
    d.text((M + 210, top + 96), li.get("unit", ""), font=_f(FB, 64), fill=t["ink"], anchor="lt")

    y = top + 250
    for s in li.get("items", [])[:5]:
        d.ellipse([M + 6, y + 14, M + 22, y + 30], fill=t["accent"])
        f = _fit(d, s, FR, 40, W - 2 * M - 40, floor=28)
        d.text((M + 42, y + 4), s, font=f, fill=t["ink"], anchor="lt")
        y += 74

    y += 30
    d.line([M, y, W - M, y], fill=t["line"], width=2)
    f = _fit(d, item["cover_sub"], FB, 48, W - 2 * M, floor=34)
    d.text((M, y + 34), item["cover_sub"], font=f, fill=t["ink"], anchor="lt")


def _cover_compare(d, item, t, W, H):
    """左「之前」右「之后」，结果用红绿区分。"""
    cp = item["compare"]
    top = 240
    f = _fit(d, item["cover_main"], FB, 62, W - 2 * M, floor=42)
    d.text((M, top), item["cover_main"], font=f, fill=t["ink"], anchor="lt")

    y = top + 120
    col_w = (W - 2 * M - 30) // 2
    for i, (lab, txt, res, color) in enumerate((
        (cp["left_label"], cp["left_text"], cp["left_result"], t["bad"]),
        (cp["right_label"], cp["right_text"], cp["right_result"], t["good"]),
    )):
        x = M + i * (col_w + 30)
        d.rounded_rectangle([x, y, x + col_w, y + 430], radius=20,
                            fill=_mix(t["bg"], t["ink"], 0.05),
                            outline=t["line"], width=2)
        d.text((x + 28, y + 28), lab, font=_f(FR, 32), fill=t["sub"], anchor="lt")
        tf = _fit(d, txt, FR, 36, col_w - 56, floor=26)
        d.text((x + 28, y + 90), txt, font=tf, fill=t["ink"], anchor="lt")
        rf = _fit(d, res, FB, 40, col_w - 56, floor=28)
        d.text((x + 28, y + 260), res, font=rf, fill=color, anchor="lt")

    y2 = y + 480
    d.line([M, y2, W - M, y2], fill=t["line"], width=2)
    sf = _fit(d, item["cover_sub"], FB, 50, W - 2 * M, floor=34)
    d.text((M, y2 + 36), item["cover_sub"], font=sf, fill=t["ink"], anchor="lt")


# ---------------------------------------------------------------- 内页
def draw_page(text, tag, idx, total, theme="light", footer=None, out="page.png"):
    """编号 + 短句 + 底部强调条。一页只说一句话。"""
    t = THEMES[theme]
    W, H = CANVAS
    img = Image.new("RGB", (W, H), t["bg"])
    d = ImageDraw.Draw(img)

    d.text((M, 90), tag, font=_f(FR, 30), fill=t["sub"], anchor="lt")

    # 编号
    d.text((M, 300), f"{idx:02d}", font=_f(FB, 96), fill=t["accent"], anchor="lt")
    d.line([M, 430, M + 120, 430], fill=t["accent"], width=6)

    # 正文：按换行拆分，自动降字号
    f = _f(FB, f0)
    for ln in lines:
        f = _fit(d, ln, FB, f0, W - 2 * M, floor=38)
    y = 500
    for ln in lines:
        d.text((M, y), ln, font=f, fill=t["ink"], anchor="lt")
        y += int(f.size * 1.5)

    # 底部强调条
    if footer:
        d.line([M, H - 260, W - M, H - 260], fill=t["line"], width=2)
        ff = _fit(d, footer, FB, 44, W - 2 * M, floor=30)
        d.text((M, H - 216), footer, font=ff, fill=t["accent"], anchor="lt")

    # 页码
    d.text((W - M, H - 90), f"{idx} / {total}", font=_f(FR, 30),
           fill=t["sub"], anchor="rs")

    _save(img, out)
    return img


def _mix(a, b, r):
    ca = tuple(int(a[i:i + 2], 16) for i in (1, 3, 5))
    cb = tuple(int(b[i:i + 2], 16) for i in (1, 3, 5))
    m = tuple(int(ca[i] + (cb[i] - ca[i]) * r) for i in range(3))
    return "#%02X%02X%02X" % m


def build_pack(items, out_dir, theme="light"):
    """一条命令出全套：每篇 1 封面 + N 内页。路径保持稳定，重出不重建队列。"""
    total = len(items)
    for it in items:
        base = os.path.join(out_dir, it["id"])
        os.makedirs(base, exist_ok=True)
        draw_cover(it, theme=theme, out=os.path.join(base, "cover.png"))
        n = len(it["pages"])
        for i, txt in enumerate(it["pages"], start=2):
            draw_page(txt, it["tag"], i, n + 1, theme=theme,
                      footer=it.get("page_footer"),
                      out=os.path.join(base, f"page{i}.png"))


if __name__ == "__main__":
    import json
    import sys
    src = sys.argv[1] if len(sys.argv) > 1 else "../examples/week1.json"
    data = json.load(open(src, encoding="utf-8"))
    build_pack(data["items"], "./out", theme=data.get("theme", "light"))
