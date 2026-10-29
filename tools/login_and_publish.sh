#!/usr/bin/env bash
# 一条命令完成 GitHub 登录 + 建仓 + 推送。
# 令牌仅在本机终端内输入（不回显、不写文件、不进聊天记录）。
#
# 用法：
#   bash tools/login_and_publish.sh
#
# 前置：先在 https://github.com/settings/tokens 生成 classic token，
#       勾选 repo（全选）、workflow、read:user。

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="$PATH:/c/Program Files/GitHub CLI:/c/Program Files (x86)/GitHub CLI"

command -v gh >/dev/null 2>&1 || { echo "未找到 gh，请先安装：winget install --id GitHub.cli"; exit 1; }

echo "────────────────────────────────────────────"
echo " Agent 自动化调教 Skill · GitHub 发布"
echo "────────────────────────────────────────────"
echo
echo "令牌获取地址：https://github.com/settings/tokens"
echo "（classic token，勾选 repo / workflow / read:user）"
echo

printf "粘贴令牌（输入不回显）: "
IFS= read -rs TOKEN
echo

if [ -z "${TOKEN}" ]; then
  echo "未输入令牌，已取消。"
  exit 1
fi

echo
echo "→ 正在登录 GitHub…"
if ! printf '%s\n' "$TOKEN" | gh auth login --with-token 2>&1; then
  echo "登录失败：令牌无效或权限不足，请重新生成后重试。"
  exit 1
fi

echo "→ 登录成功："
gh api user --jq '"  \(.login)  (id: \(.id))"' 2>/dev/null || gh auth status 2>&1 | head -3

echo
echo "→ 正在建仓并推送…"
bash "$ROOT/tools/publish.sh"

unset TOKEN
echo
echo "完成。"