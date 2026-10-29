#!/usr/bin/env bash
# 一键发布到 GitHub。
# 前置：已完成一次 gh auth login（浏览器授权，只需一次，之后永久有效）。
set -e

GH_USER="melicol2026-alt"
REPO="auto-ops-agent"
VISIBILITY="--public"   # 想改成私有就把这行换成 --private

export PATH="$PATH:/c/Program Files/GitHub CLI"

cd "$(dirname "$0")"

echo "==> 检查 GitHub 登录状态"
if ! gh auth status >/dev/null 2>&1; then
  echo ""
  echo "未登录 GitHub。请先执行一次（浏览器授权，只需一次）："
  echo ""
  echo "    gh auth login"
  echo ""
  echo "完成后重新运行本脚本即可。"
  exit 1
fi

echo "==> 检查远端仓库是否存在"
if gh repo view "$GH_USER/$REPO" >/dev/null 2>&1; then
  echo "    仓库已存在，复用"
  if ! git remote get-url origin >/dev/null 2>&1; then
    git remote add origin "https://github.com/$GH_USER/$REPO.git"
  fi
else
  echo "    创建仓库 $GH_USER/$REPO"
  gh repo create "$REPO" $VISIBILITY --source=. --remote=origin --push
fi

echo "==> 推送"
git push -u origin "$(git branch --show-current)"

echo ""
echo "完成：https://github.com/$GH_USER/$REPO"
