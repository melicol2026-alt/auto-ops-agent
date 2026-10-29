#!/usr/bin/env bash
# 一条命令完成 SSH 密钥生成 + 引导加公钥 + 建仓 + 推送。
# 走 SSH（本机 git https 直连 github.com 会卡响应体）。
#
# 用法：
#   bash tools/login_and_publish.sh
#
# 流程：确保有 ed25519 密钥 → 复制公钥到剪贴板 → 打开加 key 页 →
#       轮询等待你在网页点「Add SSH key」→ 自动建仓推送。

set -euo pipefail

GH_USER="melicol2026-alt"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# 1) 确保有密钥
if [ ! -f ~/.ssh/id_ed25519 ]; then
  echo "==> 生成 ed25519 密钥…"
  mkdir -p ~/.ssh && chmod 700 ~/.ssh
  ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519 -C "$GH_USER" -q
fi

# 2) 复制公钥 + 打开添加页
echo "==> 复制公钥到剪贴板并打开添加页…"
tr -d '\n' < ~/.ssh/id_ed25519.pub | clip.exe
explorer.exe "https://github.com/settings/ssh/new" >/dev/null 2>&1
echo ""
echo "公钥已复制。请在网页里粘贴到 Key 框，Title 随意，点「Add SSH key」。"
echo "本脚本会持续等待你完成（最长 3 分钟）…"
echo ""

# 3) 轮询等待认证成功
ok=0
for i in $(seq 1 36); do
  if ssh -o ConnectTimeout=6 -o StrictHostKeyChecking=accept-new -T git@github.com 2>&1 | grep -qi "successfully authenticated"; then
    ok=1; break
  fi
  sleep 5
done

if [ "$ok" != "1" ]; then
  echo "等待超时，尚未检测到 SSH 认证成功。请确认已点「Add SSH key」，然后重跑本脚本。"
  exit 1
fi

echo "==> SSH 已认证，开始建仓并推送…"
bash "$ROOT/tools/publish.sh"
