#!/usr/bin/env bash
# 同步上游最新 tag。
#
# 步骤：
#   1. 按上游指定提交重新收录被升级的子模块（third-party/ 等）；
#   2. 合并上游 tag；
#   3. 解决冲突：
#      - .github/workflows/：上游 CI 与本仓库无关（已删除），保持删除；
#      - third-party/ 等收录目录：保留重新收录后的内容；
#      - 其它（白名单文件）：一律失败，交人工合并。
#
# 用法：ci/sync-upstream.sh <upstream-tag>
set -euo pipefail

TAG=${1:-}
if [ -z "$TAG" ]; then
  echo "用法：$0 <upstream-tag>" >&2
  exit 2
fi

if ! git rev-parse --verify --quiet "$TAG^{commit}" >/dev/null; then
  echo "上游 tag 不存在：$TAG" >&2
  exit 2
fi

script_dir=$(dirname "$0")

echo "== 1/3 重新收录子模块 =="
"$script_dir/vendor-submodules.sh" apply "$TAG"

echo "== 2/3 合并 $TAG =="
if git merge --no-edit "$TAG"; then
  echo "合并无冲突"
else
  echo "== 3/3 解决冲突 =="
  conflicts=$(git diff --name-only --diff-filter=U)
  hard=0
  for f in $conflicts; do
    case "$f" in
      .github/workflows/*)
        # 本仓库不跑上游 CI，保持删除。
        echo "   保持删除 $f"
        git rm -q -f --ignore-unmatch -- "$f"
        ;;
      third-party/* | packaging/linux/flatpak/deps/*)
        # 收录目录：保留上面重新收录好的内容。
        echo "   保留重新收录的内容 $f"
        rm -rf "${f}"~*
        git rm -q -r --cached --ignore-unmatch -- "$f"
        git add -A -- "$f"
        ;;
      *)
        echo "::error::合并冲突（白名单文件需人工合并）：$f" >&2
        hard=1
        ;;
    esac
  done
  if [ $hard -ne 0 ]; then
    git merge --abort
    echo "::error::存在需要人工处理的冲突，已回滚合并。" >&2
    exit 1
  fi
  git commit --no-edit
fi

echo "同步完成：$TAG"
