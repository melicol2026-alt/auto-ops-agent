# Agent 自动化调教 Skill (auto-ops-agent)

> 别名：`agent自动化调教skill` · `agent 自动化调教` · `自动化运营 Agent 调教法`
>
> 把一个只会给建议的 AI Agent，调教成能自己找需求、自己选题、自己出图、自己发布、自己复盘的全自动运营执行体。

[English](#english) · [快速开始](#快速开始) · [架构](#架构) · [十条铁律](#十条铁律) · [目录](#目录结构)

---

## 为什么需要这个 Skill

大多数"运营 Agent"停在一半：它给你选题、给你文案、给你排期表，然后说"剩下的你来做"。

这不是自动化，这是把执行成本原封不动还给了人。

**本 Skill 的做法**：让 Agent 成为执行体——从发现需求到内容上线到数据回流全链路自己跑完，人只在两处出现：

1. **一次性授权登录**（物理限制，无法自动化）
2. **看汇报**

适用平台：小红书、抖音、公众号、知乎、B站、X 等任何"持续产出内容 + 运营账号"的场景。
实现样例以小红书为准，但每一层都标了平台无关的接口约定（换平台只改 3 处）。

---

## 架构

```
L0 边界层   config.py        频次上限 / 活动时段 / 熔断词表 —— 脚本越不过的硬闸
L1 采集层   collect.py       零登录公开源 + 登录态站内源，产出需求信号
L2 分析层   collect.py       供需缺口算法：稀缺度 = 需求分 × 供给缺口
L3 内容层   daily content    需求驱动选题 → 证据库取料 → 合规一票否决 → 成稿
L4 素材层   render.py        PIL 代码渲染封面/内页，零出图额度、文字 100% 准确
L5 执行层   post/engage.py   自动发布 + 自动互动 + 拟人化 + 熔断
L6 复盘层   review           真实数据回流 → 更新稀缺排序 → 反哺 L2
```

**关键**：L6 必须回流到 L2。没有回流，选题永远停在开局的假设上，跑一个月就退化成"我以为用户想要"。

---

## 十条铁律

| # | 铁律 | 违反后果 |
|---|---|---|
| 1 | **不反问，只汇报** —— 自己判断、直接执行、事后汇报 | 用户效率归零 |
| 2 | **交付定稿，不交填空卷** —— 占位符 ≤3 处且带示例值 | 用户拿到填空卷还得自己写 |
| 3 | **需求驱动，不是资源驱动** —— 先算稀缺再决定写什么 | 撞红海 |
| 4 | **证据可核验，禁止编造个人经历** | 主张无支撑，比不做更致命 |
| 5 | **合规一票否决** —— 不做"风险提示"就算完 | 限流 / 封号 |
| 6 | **风险由 Agent 扛** —— 用频次拟人化压，不推给用户 | 等于没做自动化 |
| 7 | **素材用代码渲染** —— 零额度、文字准确、风格统一 | 烧额度 + 中文乱码 + 风格漂移 |
| 8 | **门禁与放行分离** —— 状态存源码外的独立文件 | 门禁形同虚设 |
| 9 | **诚实报警：采不到 ≠ 没有** | 稀缺度虚高，选出伪机会 |
| 10 | **对上游工具做最小化改动** | 升级困难，引入未知风险 |

完整说明见 [`SKILL.md`](SKILL.md)。

---

## 快速开始

```bash
# 1. 依赖
pip install pillow requests beautifulsoup4 lxml playwright
playwright install chromium

# 2. 改配置：关键词、频次上限、profile 路径
cp scripts/config_template.py myproject/config.py

# 3. 跑一次需求采集，看赛道里什么稀缺
python scripts/collect_template.py

# 4. 写内容清单（参考 examples/week1.json），一键出图
python scripts/render_template.py mycontent.json

# 5. 首次扫码登录（唯一需要人工的一步）
python myproject/post.py --dry-run

# 6. 之后全自动
python scripts/daily_run_template.py --with-publish --rounds 1
```

---

## 目录结构

```
auto-ops-agent/
├── SKILL.md                              主文档：方法论、铁律、执行流程、反模式
├── README.md
├── references/
│   ├── 01-需求采集与稀缺度算法.md        采集源选型、评分表、三个已修缺陷
│   ├── 02-内容生产与合规过滤.md          选题规则、成稿模板、合规红线
│   ├── 03-视觉版式规范.md                三种封面版式、配色、渲染坑
│   ├── 04-执行层与风控设计.md            7 道防封闸、登录态复用、门禁
│   ├── 05-证据库与引用规范.md            引用硬规则、截图脱敏清单
│   └── 06-汇报与迭代机制.md              汇报模板、自动化 prompt 模板、回流
├── scripts/
│   ├── config_template.py                风控配置骨架
│   ├── collect_template.py               需求采集骨架（含 fetch_ok 防御）
│   ├── render_template.py                封面/内页渲染骨架（三种版式 + 深浅主题）
│   └── daily_run_template.py             总调度骨架（发布 + 互动 + 出汇报）
└── examples/
    └── week1.json                        内容清单完整样例（5 篇，含版式字段）
```

---

## 防封号：7 道闸

| # | 闸 | 做法 |
|---|---|---|
| 1 | 频次硬限 | 发布 1/天、评论 3/天、点赞 8/天、收藏 3/天、**关注 0** |
| 2 | 真实浏览器 + 持久化 profile | 系统 Chrome/Edge，脚本不碰 Cookie |
| 3 | 随机间隔 + 作息时段 | 8–25 分钟随机；只在 9–11 / 14–16 / 20–22 活动 |
| 4 | 先阅读再操作 | 进笔记先分段滚动再点赞/评论 |
| 5 | 只在同赛道内容下活动 | 保证人群相关，避免行为画像漂移 |
| 6 | 风控词熔断 | 出现"验证/异常/操作频繁"立即中止当日任务 |
| 7 | 高危动作不排期 | 批量关注、私信、导流、刷量——不写代码 |

---

## 反模式清单

| 反模式 | 正确做法 |
|---|---|
| 把执行动作推回用户 | 自己设计风控后执行 |
| 用大量占位符交付 | 自己定稿，占位符 ≤3 处且带示例值 |
| 用户有什么就写什么 | 先算稀缺再选题 |
| 把"采不到"当"没人做" | 明确标注数据不可用 |
| 封面有主张无证据 | 主张必须配可核验证据 |
| 深色大字报做封面 | 暖色底 + 信息量可视化 |
| 用模型出图做封面 | 代码渲染 |
| 拿 URL 判断登录态 | 以"页面真的出现发布入口"为准 |
| 单方面替用户决定不做自动发布 | 量化风险、设防、执行、汇报 |
| 自动化自行放行门禁 | 放行状态存独立文件 |

---

## 平台适配

换平台只改三处，其余架构不变：

1. `config.py` → `TARGET_KEYWORDS`、`ABORT_SIGNALS`、频次上限
2. `post.py` / `engage.py` → 选择器与 URL
3. `render.py` → 画布尺寸（小红书 1080×1440，抖音 1080×1920，公众号 900×500）

---

## 免责声明

- 自动化发布与互动在多数平台的用户协议下属灰区。本 Skill 提供的风控设计可以把风险压到很低，**但不是零**——这是"全自动"的固有代价，使用者需自行判断。
- 采集部分只访问无需登录的公开页面与公开接口；涉及登录态的方案需使用者本人扫码授权，且不得采集用户个人信息。
- 第三方工具（如 MediaCrawler）的使用条款以其官方声明为准，用于自有账号选题调研的合规性由使用者自行判断。

---

## English

Turn a suggestion-only AI assistant into an autonomous operations agent that finds demand,
picks topics, renders visuals, publishes, and reviews on its own.

Six layers (boundary → collection → analysis → content → creatives → execution → review),
ten hard rules (never ask back, ship finished drafts not templates, demand-driven not
resource-driven, verifiable evidence only, compliance veto, agent absorbs the risk,
code-rendered creatives, separated approval gate, honest failure reporting, minimal
upstream changes), seven anti-ban throttles, and reusable script skeletons.

Start with [`SKILL.md`](SKILL.md).
