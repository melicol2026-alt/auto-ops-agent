#!/usr/bin/env bash
# 通过 SSH 推送到 GitHub。
# 注意：本机 git https 直连 github.com 会卡在响应体（git 内置旧 libcurl 的 schannel 重协商 bug），
#       SSH（22 端口）稳定，故统一走 SSH。
set -euo pipefail

GH_USER="melicol2026-alt"
REPO="auto-ops-agent"
BRANCH="main"

cd "$(dirname "$0")/.."

# 1) SSH 认证检查
if ! ssh -o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new -T git@github.com 2>&1 | grep -qi "successfully authenticated"; then
  echo "SSH 未认证到 GitHub。请先加公钥："
  echo "  1) 若无密钥：ssh-keygen -t ed25519 -N '' -f ~/.ssh/id_ed25519 -C '$GH_USER'"
  echo "  2) 复制公钥：clip.exe < ~/.ssh/id_ed25519.pub"
  echo "  3) 打开 https://github.com/settings/ssh/new 粘贴并保存"
  echo "  4) 重跑本脚本"
  exit 1
fi

# 2) 确保 origin 指向 SSH
if ! git remote get-url origin >/dev/null 2>&1; then
  git remote add origin "git@github.com:$GH_USER/$REPO.git"
else
  git remote set-url origin "git@github.com:$GH_USER/$REPO.git"
fi

# 3) 仓库不存在时尝试用 GH_PAT 建仓（可选）
if ! git ls-remote --exit-code origin >/dev/null 2>&1; then
  if [ -n "${GH_PAT:-}" ]; then
    echo "==> 远端仓库不存在，用 GH_PAT 创建 public 仓库 $GH_USER/$REPO"
    curl -sf -X POST https://api.github.com/user/repos \
      -H "Authorization: token $GH_PAT" -H "Accept: application/vnd.github+json" \
      -d "{\"name\":\"$REPO\",\"private\":false}" >/dev/null || {
        echo "建仓失败：GH_PAT 权限不足（需 repo scope），或仓库名已被占用。"
        exit 1
      }
  else
    echo "远端仓库不存在。请先手动建仓：https://github.com/new?name=$REPO （public）"
    echo "或设置 GH_PAT 环境变量后重跑本脚本自动建仓。"
    exit 1
  fi
fi

# 4) 推送
echo "==> 推送 $BRANCH"
git push -u origin "$BRANCH"

echo ""
echo "完成：https://github.com/$GH_USER/$REPO"
