# -*- coding: utf-8 -*-
"""需求采集骨架：零登录公开源优先，采不到要如实标注。

三个必须实现的防御（否则产出的数据会骗人）：
1. 噪音词过滤     —— 联想词会混入完全无关的词
2. fetch_ok 标记  —— 采不到 ≠ 没有，未采到的禁止判为空白
3. 词归一化       —— 大小写/空格/全半角不统一会稀释需求信号
"""

import json
import os
import re
import time
from collections import Counter
from datetime import datetime

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
TIMEOUT = 10
POLITE = (1.5, 3.0)   # 请求间隔，别把人家限流了

SEED_WORDS = ["示例种子词一", "示例种子词二"]
DOMAIN_WORDS = ("示例", "领域")        # 领域白名单，用于过滤噪音
CLICHE_WORDS = ("保姆级", "绝了", "必看", "最强", "吐血整理")


def polite_sleep():
    time.sleep(POLITE[0])


def _safe(fn, default):
    """任何采集失败都返回默认值，绝不抛异常中断整轮。"""
    try:
        return fn()
    except Exception:
        return default


def normalize(word):
    """归一化：小写 + 去空格 + 全角转半角。"""
    w = word.strip().lower().replace(" ", "")
    w = "".join(chr(ord(c) - 0xFEE0) if 0xFF01 <= ord(c) <= 0xFF5E else c for c in w)
    return w


def is_noise(word):
    """噪音判定：不在领域白名单内，或与种子词无任何字面重叠。"""
    if len(word) < 3:
        return True
    if DOMAIN_WORDS and not any(d in word for d in DOMAIN_WORDS):
        return True
    return False


def suggest_baidu(kw):
    """百度下拉联想：真实搜索需求词。返回词列表 + fetch_ok。"""
    def _go():
        r = requests.get("https://suggestion.baidu.com/su",
                         params={"wd": kw}, headers=HEADERS, timeout=TIMEOUT)
        r.encoding = "gbk"
        items = re.findall(r's:\[(.*?)\]', r.text)
        if not items:
            return [], False
        words = re.findall(r'"(.*?)"', items[0])
        return words, True
    out = _safe(_go, ([], False))
    return out if isinstance(out, tuple) else ([], False)


def suggest_360(kw):
    """360 下拉：与百度交叉验证，只出现在单一源的降权。"""
    def _go():
        r = requests.get("https://sug.so.360.cn/suggest",
                         params={"word": kw}, headers=HEADERS, timeout=TIMEOUT)
        data = r.json()
        words = [x.get("word", "") for x in data.get("result", [])]
        return [w for w in words if w], True
    out = _safe(_go, ([], False))
    return out if isinstance(out, tuple) else ([], False)


def search_supply(query):
    """公开搜索供给侧。**必须返回 fetch_ok** —— 被限流时不能当成"没供给"。"""
    def _go():
        r = requests.get("https://www.bing.com/search",
                         params={"q": query, "count": "20"},
                         headers=HEADERS, timeout=TIMEOUT)
        soup = BeautifulSoup(r.text, "lxml")
        titles = [h.get_text(strip=True) for h in soup.select("h2") if h.get_text(strip=True)]
        return titles[:20], True
    titles, ok = _safe(_go, ([], False))
    # 检测限流/异常：0 条或恒为固定条数都要标记不可靠
    if not titles:
        return titles, False
    return titles, ok


def score(word, source_count, titles, fetch_ok):
    """稀缺度评分。fetch_ok=False 时供给一律按"未知"处理，不给分。"""
    need = 0
    need += 2 if source_count >= 2 else 0          # 跨源重复 = 需求更真
    need += 2 if any(k in word for k in ("怎么办", "如何", "为什么", "怎么", "哪些")) else 0
    need += 2 if len(word) >= 5 else 0             # 长尾更具体

    supply, detail = 0, []
    if not fetch_ok:
        detail.append("供给数据缺失，暂不能判定为空白")
        return need, supply, detail, False

    c = len(titles)
    if c >= 15:
        supply += 4; detail.append(f"供给饱和({c}条)")
    elif c >= 8:
        supply += 3; detail.append(f"供给较多({c}条)")
    elif c >= 3:
        supply += 2; detail.append(f"供给较少({c}条)")

    cr = (sum(1 for t in titles if any(x in t for x in CLICHE_WORDS)) / c) if c else 0
    if cr >= 0.5:
        supply += 4; detail.append(f"标题套路化严重({cr:.0%})")
    elif cr >= 0.3:
        supply += 2; detail.append(f"标题部分套路化({cr:.0%})")

    return need, supply, detail, True


def collect(seeds=None):
    seeds = seeds or SEED_WORDS
    demand = Counter()
    sources = {}
    for kw in seeds:
        for fn, name in ((suggest_baidu, "baidu"), (suggest_360, "360")):
            words, ok = fn(kw)
            if not ok:
                print(f"  ! {name} 采集失败（{kw}），本轮标记为不可用")
            for w in words:
                w = normalize(w)
                if is_noise(w):
                    continue
                demand[w] += 1
                sources.setdefault(w, set()).add(name)
            polite_sleep()

    rows = []
    for w, _ in demand.most_common(10):
        titles, fetch_ok = search_supply(w)
        polite_sleep()
        need, supply, detail, ok = score(w, len(sources.get(w, ())), titles, fetch_ok)
        rows.append({
            "word": w, "need": need, "scarcity": supply,
            "fetch_ok": ok, "detail": detail, "titles": titles[:3],
        })

    return {"date": datetime.now().strftime("%Y-%m-%d"), "rows": rows}


def render_md(data):
    L = [f"# 需求信号报告 {data['date']}\n"]
    missing = [r for r in data["rows"] if not r["fetch_ok"]]
    if missing:
        L.append("> **数据质量提示**："
                 f"本次有 {len(missing)} 个词的供给数据缺失，"
                 "只能作观察项，禁止当作空白机会。\n")
    L.append("| 需求词 | 需求分 | 稀缺度 | 数据完整 | 说明 |")
    L.append("|---|---|---|---|---|")
    for r in data["rows"]:
        flag = "是" if r["fetch_ok"] else "**否**"
        L.append(f"| {r['word']} | {r['need']} | {r['scarcity']} | {flag} "
                 f"| {'；'.join(r['detail']) or '无'} |")
    return "\n".join(L)


def main():
    data = collect()
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
    os.makedirs(out_dir, exist_ok=True)
    json.dump(data, open(os.path.join(out_dir, "demand.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    md = render_md(data)
    open(os.path.join(out_dir, "latest.md"), "w", encoding="utf-8").write(md)
    print(md)


if __name__ == "__main__":
    main()
