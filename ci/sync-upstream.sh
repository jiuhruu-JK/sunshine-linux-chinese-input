#!/usr/bin/env bash
# 同步上游最新 tag。
#
# 步骤：
#   0. 若仓库还没有与上游的共同祖先（刚建 fork、还没接上上游历史），
#      先用 -s ours 接上祖先关系：只记录合并，不改工作树；
#   1. 按上游指定提交重新收录被升级的子模块；
#   2. 合并上游 tag；
#   3. 解决冲突：
#      - .github/workflows/：上游 CI 与本仓库无关（已删除），保持删除；
#      - 收录目录：保留重新收录后的内容；
#      - 白名单文件：取上游版本，再把我们相对基线的改动打回去；
#      - 其它：一律失败，交人工合并。
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
baseline_file="upstream-baseline"

# 白名单文件：与 ci/check-boundary.sh 保持一致
whitelist=(
  src/platform/linux/input_method.h
  src/platform/linux/input_method.cpp
  src/platform/virtualhid_input.cpp
  src/process.cpp
  src/stream.cpp
  cmake/compile_definitions/linux.cmake
  tests/unit/platform/linux/test_input_method.cpp
)

baseline=$(cat "$baseline_file" 2>/dev/null || true)

# --- 0. 接上上游祖先关系 --------------------------------------------------
if [ -n "$baseline" ] && ! git merge-base --is-ancestor "$baseline" HEAD 2>/dev/null; then
  echo "== 0/3 接上上游祖先关系（$baseline）=="
  git merge -s ours --allow-unrelated-histories "$baseline" \
    -m "chore: 接上上游祖先关系（不改动任何文件）"
fi

# --- 1. 重新收录子模块 ----------------------------------------------------
echo "== 1/3 重新收录子模块 =="
"$script_dir/vendor-submodules.sh" apply "$TAG"

# 我们相对基线在白名单文件上的改动，冲突时打回上游版本上
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
ours_patch="$work/ours.patch"
if [ -n "$baseline" ]; then
  git diff "$baseline" HEAD -- "${whitelist[@]}" >"$ours_patch" || true
fi

# --- 2. 合并上游 tag ------------------------------------------------------
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
      *~*)
        # 目录阻挡：我们的目录挡住了上游的子模块条目，git 把我们的目录挪成了
        # <路径>~<提交>，冲突记录在挪名之后的路径上。保留重新收录好的内容。
        orig="${f%%~*}"
        echo "   保留重新收录的内容 $orig"
        rm -rf -- "$f"
        git rm -q -r --cached --ignore-unmatch -- "$f"
        git add -A -- "$orig"
        ;;
      third-party/* | packaging/linux/flatpak/deps/*)
        # 上游新增/删除的收录目录：按上面的重新收录结果为准。
        echo "   按重新收录结果处理 $f"
        git rm -q -r --cached --ignore-unmatch -- "$f"
        git add -A -- "$f"
        ;;
      *)
        # 白名单文件：取上游版本，再把我们相对基线的改动打回去。
        is_whitelist=0
        for w in "${whitelist[@]}"; do
          [ "$f" = "$w" ] && is_whitelist=1 && break
        done
        if [ $is_whitelist -eq 1 ] && [ -s "$ours_patch" ]; then
          echo "   取上游版本并重放我们的改动 $f"
          git checkout --theirs -- "$f"
          if git apply --3way --include="$f" "$ours_patch"; then
            git add -- "$f"
          else
            echo "::error::$f 上我们的改动与上游改动冲突，需人工合并" >&2
            hard=1
          fi
        else
          echo "::error::合并冲突（需人工合并）：$f" >&2
          hard=1
        fi
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

# --- 记录新的基线 --------------------------------------------------------
git rev-parse "$TAG^{commit}" >"$baseline_file"

echo "同步完成：$TAG（基线 $(cat "$baseline_file")）"
