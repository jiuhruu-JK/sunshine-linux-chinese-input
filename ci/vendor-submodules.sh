#!/usr/bin/env bash
# 收录上游子模块内容。
#
# 本仓库把上游的子模块按目录形态收录进仓库（不保留 git submodule 结构），
# 这样克隆下来就能直接构建。收录内容必须与上游指定提交逐字节一致，
# 否则构建出来的产物与上游对不上。
#
# 用法：
#   ci/vendor-submodules.sh check <upstream-ref>        # 只核对，不改动
#   ci/vendor-submodules.sh apply <upstream-ref>        # 把有差异的子模块重新收录
#   ci/vendor-submodules.sh apply <upstream-ref> --all  # 全部重新收录（用来查残留）
#
# 收录清单记录在 ci/vendored-submodules.txt：每行 "<提交> <路径>"。
set -euo pipefail

MODE=${1:-check}
UPSTREAM_REF=${2:-}
ALL=false
if [ "${3:-}" = "--all" ]; then
  ALL=true
fi
MANIFEST="$(dirname "$0")/vendored-submodules.txt"

if [ -z "$UPSTREAM_REF" ]; then
  echo "用法：$0 <check|apply> <upstream-ref>" >&2
  exit 2
fi

if ! git rev-parse --verify --quiet "$UPSTREAM_REF^{commit}" >/dev/null; then
  echo "上游引用不存在：$UPSTREAM_REF" >&2
  exit 2
fi

# 有意不收录的上游子模块（与 ci/check-boundary.sh 的清单一致）
SKIP=(
  third-party/build-deps
  third-party/ViGEmClient
  third-party/TPCircularBuffer
)

is_skipped() {
  local candidate=$1
  local item
  for item in "${SKIP[@]}"; do
    [ "$candidate" = "$item" ] && return 0
  done
  return 1
}

# 上游树里该路径的子模块提交
upstream_pin() {
  git ls-tree -r "$UPSTREAM_REF" -- "$1" | awk '$1 == "160000" { print $3; exit }'
}

# 清单里记录的提交
manifest_pin() {
  awk -v path="$1" '$2 == path { print $1; exit }' "$MANIFEST"
}

# .gitmodules 里登记的地址
submodule_url() {
  git config -f .gitmodules --get "submodule.$1.url" || true
}

stale=()
while IFS= read -r path; do
  [ -z "$path" ] && continue
  is_skipped "$path" && continue
  want=$(upstream_pin "$path")
  [ -z "$want" ] && continue
  have=$(manifest_pin "$path")
  if [ "$want" != "$have" ] || [ "$ALL" = true ]; then
    stale+=("$path")
  fi
done < <(git ls-tree -r --name-only "$UPSTREAM_REF" -- third-party/ packaging/linux/flatpak/deps/ | sort -u)

if [ ${#stale[@]} -eq 0 ]; then
  echo "收录内容与上游 $UPSTREAM_REF 一致"
  exit 0
fi

if [ "$MODE" = "check" ]; then
  echo "以下子模块需要按上游 $UPSTREAM_REF 重新收录：" >&2
  printf '  %s\n' "${stale[@]}" >&2
  echo "执行 $0 apply $UPSTREAM_REF 重新收录。" >&2
  exit 1
fi

if [ "$MODE" != "apply" ]; then
  echo "用法：$0 <check|apply> <upstream-ref>" >&2
  exit 2
fi

tmp_root=$(mktemp -d)
trap 'rm -rf "$tmp_root"' EXIT

for path in "${stale[@]}"; do
  want=$(upstream_pin "$path")
  url=$(submodule_url "$path")
  if [ -z "$url" ]; then
    echo "::error::.gitmodules 里没有 $path 的地址" >&2
    exit 1
  fi
  echo "重新收录 $path @ $want"
  work="$tmp_root/$(echo "$path" | tr '/' '_')"
  git clone --quiet --filter=blob:none --no-checkout "$url" "$work"
  git -C "$work" checkout --quiet "$want"
  git -C "$work" submodule update --init --recursive --quiet

  rm -rf "$path"
  mkdir -p "$path"
  (cd "$work" && tar --exclude='.git' --exclude='*/.git' -cf - .) | (cd "$path" && tar -xf -)
  rm -rf "$work"

  # 更新清单
  tmp_manifest=$(mktemp)
  awk -v path="$path" -v pin="$want" '$2 == path { print pin " " path; next } { print }' \
    "$MANIFEST" >"$tmp_manifest"
  mv "$tmp_manifest" "$MANIFEST"
done

sort -o "$MANIFEST" "$MANIFEST"
echo "收录完成，清单已更新：$MANIFEST"
