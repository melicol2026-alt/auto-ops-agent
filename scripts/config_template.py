# -*- coding: utf-8 -*-
"""风控配置骨架。

这些数字是防封号设计，不是性能参数。
任何"为了让任务完成得更多"而调高它们的改动，都是在赌账号。

平台适配：换平台只改本文件的 TARGET_KEYWORDS / ABORT_SIGNALS / LIMITS。
"""

import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

# ---------------------------------------------------------------- 浏览器
# 真实浏览器 + 持久化 profile：登录一次永久复用，脚本不碰 Cookie
BROWSER_CANDIDATES = (
    ("C:/Program Files/Google/Chrome/Application/chrome.exe", "chrome"),
    ("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe", "chrome"),
    ("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe", "msedge"),
    ("C:/Program Files/Microsoft/Edge/Application/msedge.exe", "msedge"),
)
PROFILE_DIR = os.path.join(ROOT, ".runtime", "profile")

# ---------------------------------------------------------------- 频次硬限
# 脚本自身越不过。调高 = 提高封号概率。
LIMITS = {
    "publish_per_day": 1,
    "comment_per_day": 3,
    "like_per_day": 8,
    "collect_per_day": 3,
    "follow_per_day": 0,      # 批量关注是封号重灾区，直接归零
    "dm_per_day": 0,          # 不排期
}

# ---------------------------------------------------------------- 拟人化
ACTION_GAP_MIN = 8 * 60      # 两次动作最小间隔（秒）
ACTION_GAP_MAX = 25 * 60
DWELL_MIN = 2                # 页面停留
DWELL_MAX = 5
SCROLL_MIN = 2               # 分段滚动次数
SCROLL_MAX = 5

# 只在真人作息时段活动
ACTIVE_HOURS = ((9, 11), (14, 16), (20, 22))

# ---------------------------------------------------------------- 熔断
ABORT_SIGNALS = (
    "验证", "异常", "操作频繁", "请稍后再试", "存在风险",
    "已被限制", "滑块", "安全验证", "账号异常",
)

# ---------------------------------------------------------------- 互动范围
# 只在同赛道内容下活动：既保证人群相关，也避免行为画像漂移
TARGET_KEYWORDS = [
    "示例关键词一",
    "示例关键词二",
]

# ---------------------------------------------------------------- 门禁
APPROVAL_GATE = {
    "enabled": True,
    "first_n": 3,
}
# 放行状态放源码之外，自动化改不了
APPROVED_FILE = os.path.join(ROOT, ".runtime", "approved.json")

# ---------------------------------------------------------------- 合规预检
FORBIDDEN_PATTERNS = (
    "月入", "躺赚", "保证", "100%", "彻底解决", "最强", "第一", "唯一",
    "加微信", "私信我", "扫码领取", "点击链接",
)

# ---------------------------------------------------------------- 路径
QUEUE_FILE = os.path.join(ROOT, "data", "publish_queue.json")
COMMENTS_FILE = os.path.join(ROOT, "data", "engagement", "comments_queue.json")
LOG_FILE = os.path.join(ROOT, ".runtime", "actions.log")
REPORT_FILE = os.path.join(ROOT, ".runtime", "report.md")
SHOT_DIR = os.path.join(ROOT, ".runtime", "shots")


def within_active_hours(hour=None):
    """当前是否处于允许操作的时段。"""
    from datetime import datetime
    h = hour if hour is not None else datetime.now().hour
    return any(a <= h < b for a, b in ACTIVE_HOURS)
