#!/usr/bin/env bash
# 核对收录的第三方依赖是否与上游指定提交逐字节一致。
#
# 做法：按上游 pin 把每个收录目录重新生成一遍，然后要求工作树没有变化。
#
# 这样能抓住两类问题：
#   1. 有人在收录目录里塞了本仓库的改动（门禁对 third-party 不比对，
#      这类改动以前能藏住）；
#   2. 上游 pin 变了而收录内容没跟上。
#
# 用法：ci/check-vendored.sh <upstream-ref>
set -euo pipefail

UPSTREAM_REF=${1:-}
if [ -z "$UPSTREAM_REF" ]; then
  echo "用法：$0 <upstream-ref>" >&2
  exit 2
fi

if ! git rev-parse --verify --quiet "$UPSTREAM_REF^{commit}" >/dev/null; then
  echo "上游引用不存在：$UPSTREAM_REF" >&2
  exit 2
fi

script_dir=$(dirname "$0")

# 重新生成全部收录内容
"$script_dir/vendor-submodules.sh" apply "$UPSTREAM_REF" --all

changed=$(git status --porcelain)
if [ -n "$changed" ]; then
  echo "::error::收录的第三方依赖与上游 $UPSTREAM_REF 不一致：" >&2
  printf '%s\n' "$changed" | head -50 >&2
  echo "重新生成结果见上面的差异；若确实是上游 pin 变了，用" >&2
  echo "  ci/vendor-submodules.sh apply $UPSTREAM_REF --all" >&2
  echo "重新收录后提交即可。" >&2
  exit 1
fi

echo "收录内容与上游 $UPSTREAM_REF 一致"
