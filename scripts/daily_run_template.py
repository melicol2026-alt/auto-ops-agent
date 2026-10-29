# -*- coding: utf-8 -*-
"""总调度骨架：一次运行完成 发布 + 互动 + 出汇报。

设计原则：
1. 频次从 config 读，脚本自身越不过 —— 用完就停，不补量
2. 未登录立刻退出，绝不以游客身份操作
3. 任何异常都记进日志与报告，不静默跳过
4. 命中风控词立即熔断，当日不再做任何动作

用法：
    python daily_run.py                     # 只互动
    python daily_run.py --with-publish      # 发布 + 互动
    python daily_run.py --rounds 2          # 互动轮次
"""

import argparse
import json
import os
import random
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402

# 说明：browser / post / engage 按平台实现，需至少提供：
#   browser.ensure_login(wait_login=False) -> (pw, ctx, page)
#   browser.sleep_random(a, b) / human_scroll(page) / page_has_abort_signal(page)
#   post.publish(item, dry_run, page) -> (ok, msg)
#   engage.run_round(page, limits) -> dict


def _load_json(path, default):
    if not os.path.exists(path):
        return default
    return json.load(open(path, encoding="utf-8"))


def _save_json(path, data):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def today_key():
    return datetime.now().strftime("%Y-%m-%d")


def usage_today():
    """读取当日用量；跨天自动归零。"""
    p = os.path.join(os.path.dirname(config.LOG_FILE), "usage.json")
    data = _load_json(p, {"date": today_key(), "used": {}})
    if data.get("date") != today_key():
        data = {"date": today_key(), "used": {}}
    return data


def bump_usage(kind, n=1):
    data = usage_today()
    data["used"][kind] = data["used"].get(kind, 0) + n
    _save_json(os.path.join(os.path.dirname(config.LOG_FILE), "usage.json"), data)


def remaining(kind):
    used = usage_today()["used"].get(kind, 0)
    return max(0, config.LIMITS.get(f"{kind}_per_day", 0) - used)


def compliance_check(text):
    """发布前合规预检：命中红线直接拒发。"""
    hits = [p for p in config.FORBIDDEN_PATTERNS if p in text]
    return (not hits), hits


def gate_status(item_id, index):
    """门禁：前 N 篇必须先试跑，放行状态在源码之外。"""
    g = config.APPROVAL_GATE
    if not g.get("enabled"):
        return False, "门禁未启用"
    approved = _load_json(config.APPROVED_FILE, {"ids": []}).get("ids", [])
    if item_id in approved:
        return False, "已放行"
    if index < g.get("first_n", 0):
        return True, f"前 {g['first_n']} 篇需人工检查，本次只试跑不发布"
    return False, "无需门禁"


def do_publish(page, log):
    queue = _load_json(config.QUEUE_FILE, [])
    if not queue:
        log("发布队列为空，跳过发布")
        return "未发布（队列为空）"

    for i, item in enumerate(queue):
        if item.get("published"):
            continue
        gated, why = gate_status(item.get("id", f"i{i}"), i)
        log(f"取篇目 {item.get('id')}：{why}")

        ok, hits = compliance_check(item.get("note_title", "") + "\n" + item.get("body", ""))
        if not ok:
            log(f"合规预检未通过，拒发：{hits}")
            return f"拒发（合规：{hits}）"

        success, msg = post.publish(item, dry_run=gated, page=page)  # noqa: F821
        if success and not gated:
            item["published"] = True
            item["published_at"] = datetime.now().isoformat(timespec="seconds")
            _save_json(config.QUEUE_FILE, queue)
            bump_usage("publish")
        log(f"发布结果：{msg}")
        return msg
    return "队列已全部发布"


def do_engage(page, rounds, log):
    done = {"like": 0, "collect": 0, "comment": 0}
    for r in range(rounds):
        if page_has_abort(page):  # noqa: F821
            log("命中风控信号，当日任务熔断")
            return done, True
        if not config.within_active_hours():
            log("非活动时段，跳过本轮")
            break
        got = engage.run_round(page, {k: remaining(k) for k in done})  # noqa: F821
        for k, v in got.items():
            done[k] += v
            if v:
                bump_usage(k, v)
        if r < rounds - 1:
            time.sleep(random.uniform(config.ACTION_GAP_MIN, config.ACTION_GAP_MAX))
    return done, False


def page_has_abort(page):
    try:
        txt = page.inner_text("body")[:4000].lower()
    except Exception:
        return False
    return any(s.lower() in txt for s in config.ABORT_SIGNALS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--with-publish", action="store_true")
    ap.add_argument("--rounds", type=int, default=1)
    args = ap.parse_args()

    os.makedirs(os.path.dirname(config.LOG_FILE), exist_ok=True)
    lines = []

    def log(msg):
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{stamp} {msg}"
        lines.append(line)
        print(line, flush=True)
        with open(config.LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    log("=== 每日任务开始 ===")
    publish_result = "未执行"
    engaged = {"like": 0, "collect": 0, "comment": 0}
    aborted = False

    try:
        pw, ctx, page = browser.ensure_login(wait_login=False)  # noqa: F821
    except RuntimeError as e:
        log(f"中止：{e}")
        _write_report(lines, "未执行（未登录）", engaged, True, str(e))
        return

    try:
        if args.with_publish and remaining("publish") > 0:
            publish_result = do_publish(page, log)
        elif args.with_publish:
            publish_result = "未发布（当日发布额度已用完）"
        engaged, aborted = do_engage(page, args.rounds, log)
    except Exception as e:
        log(f"执行异常：{type(e).__name__}: {e}")
        aborted = True
    finally:
        try:
            ctx.close()
            pw.stop()
        except Exception:
            pass

    log("=== 每日任务结束 ===")
    _write_report(lines, publish_result, engaged, aborted, None)


def _write_report(lines, publish_result, engaged, aborted, err):
    q = _load_json(config.QUEUE_FILE, [])
    left = sum(1 for x in q if not x.get("published"))
    cmts = _load_json(config.COMMENTS_FILE, [])
    used = usage_today()["used"]

    md = [
        f"# 运营执行汇报 {today_key()}\n",
        f"**发布**：{publish_result}",
        f"**互动**：点赞 {engaged['like']} ｜ 收藏 {engaged['collect']} ｜ 评论 {engaged['comment']}",
        f"**当日累计**：" + " ｜ ".join(f"{k} {v}/{config.LIMITS.get(k + '_per_day', 0)}"
                                    for k, v in used.items()),
        f"**队列**：剩余待发布 {left} 篇 ｜ 评论池剩余 {len(cmts)} 条",
        f"**熔断**：{'是' if aborted else '否'}" + (f"（{err}）" if err else ""),
        "",
        "## 执行日志",
        "```",
        *lines,
        "```",
    ]
    if left == 0:
        md.insert(5, "> **提示**：发布队列已空，需要生成下批内容。")
    if len(cmts) < 4:
        md.insert(6, "> **提示**：评论池不足 4 条，需要补充。")

    open(config.REPORT_FILE, "w", encoding="utf-8").write("\n".join(md))
    print("\n汇报已写入", config.REPORT_FILE)


if __name__ == "__main__":
    main()
