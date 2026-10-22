#!/usr/bin/env bash
# 边界门禁：确认相对上游的改动只落在"文本输入"相关文件里。
# 用法：ci/check-boundary.sh <upstream-ref>
set -euo pipefail

UPSTREAM_REF=${1:-}
if [ -z "$UPSTREAM_REF" ]; then
  echo "usage: $0 <upstream-ref>" >&2
  exit 2
fi

# 唯一允许与上游不同的源码文件
ALLOW=(
  src/platform/linux/input_method.h
  src/platform/linux/input_method.cpp
  src/process.cpp
  src/stream.cpp
  cmake/compile_definitions/linux.cmake
  src/unit/platform/linux/test_input_method.cpp
)

# 仓库自有内容，不参与和上游比对
OWN=(
  README.md
  flake.nix
  upstream-version
  nix/
  ci/
  .github/
  fcitx5-plugin/
)

fail=0
while IFS= read -r f; do
  [ -z "$f" ] && continue
  ok=0
  for p in "${ALLOW[@]}"; do
    [ "$f" = "$p" ] && ok=1 && break
  done
  if [ $ok -eq 0 ]; then
    for p in "${OWN[@]}"; do
      case "$f" in "$p"*) ok=1; break ;; esac
    done
  fi
  if [ $ok -eq 0 ]; then
    echo "::error::越界改动：$f"
    fail=1
  fi
done < <(git diff --name-only "$UPSTREAM_REF" HEAD)

if [ $fail -ne 0 ]; then
  echo "边界检查失败：以上文件不属于文本输入改动范围。" >&2
  exit 1
fi
echo "边界检查通过"
