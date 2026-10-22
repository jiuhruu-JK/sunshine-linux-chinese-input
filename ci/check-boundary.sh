#!/usr/bin/env bash
# 边界门禁：确认相对上游的改动只落在"文本输入"相关文件里。
#
# 用法：ci/check-boundary.sh <upstream-ref>
#
# 规则（与 docs/sunshine-cn-input-ARCHITECTURE.md 第 4.2 节一致）：
#   1. ALLOW  —— 唯一允许与上游不同的源码文件；
#   2. ADD_ONLY —— 允许不同的文件里只准新增行，不准删改上游已有代码；
#   3. OWN —— 仓库自有内容，不与上游比对；
#   4. VENDORED —— 收录进仓库的上游子模块内容（目录形态），不与上游比对，
#      但必须逐个核对上游的子模块清单，防止上游新增/删除子模块后本仓库悄悄缺料。
set -euo pipefail

UPSTREAM_REF=${1:-}
if [ -z "$UPSTREAM_REF" ]; then
  echo "usage: $0 <upstream-ref>" >&2
  exit 2
fi

if ! git rev-parse --verify --quiet "$UPSTREAM_REF^{commit}" >/dev/null; then
  echo "::error::上游引用不存在：$UPSTREAM_REF" >&2
  exit 2
fi

# 唯一允许与上游不同的源码文件
ALLOW=(
  src/platform/linux/input_method.h
  src/platform/linux/input_method.cpp
  src/platform/virtualhid_input.cpp
  src/process.cpp
  src/stream.cpp
  cmake/compile_definitions/linux.cmake
  tests/unit/platform/linux/test_input_method.cpp
)

# 这些文件只准新增行：挂钩子的地方不许删改上游已有代码
ADD_ONLY=(
  src/platform/virtualhid_input.cpp
  src/process.cpp
  src/stream.cpp
  cmake/compile_definitions/linux.cmake
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
  docs/UPSTREAM-README.md
  docs/sunshine-cn-input-ARCHITECTURE.md
  docs/sunshine-cn-input-IMPLEMENTATION.md
)

# 收录进仓库的上游子模块内容（目录形态），不参与比对
VENDORED=(
  third-party/
  packaging/linux/flatpak/deps/
)

# 上游子模块清单里、本仓库有意不收录的条目（理由见行尾注释）。
# 上游新增任何不在此表里的子模块时，边界检查会立刻报错。
NOT_VENDORED=(
  third-party/build-deps      # 只用到它的 package-lock.cmake，nix 打包时单独 fetch
  third-party/ViGEmClient     # 只被 Windows 端的虚拟手柄后端使用
  third-party/TPCircularBuffer # 收录版 moonlight-common-c 不引用它
)

fail=0

# --- 1. 文件白名单 -------------------------------------------------------
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
    for p in "${VENDORED[@]}"; do
      case "$f" in "$p"*) ok=1; break ;; esac
    done
  fi
  if [ $ok -eq 0 ]; then
    echo "::error::越界改动：$f"
    fail=1
  fi
done < <(git diff --name-only "$UPSTREAM_REF" HEAD)

# --- 2. 挂钩子文件只准新增行 ---------------------------------------------
for p in "${ADD_ONLY[@]}"; do
  removed=$(git diff -U0 "$UPSTREAM_REF" HEAD -- "$p" | grep -c '^-[^-]' || true)
  if [ "$removed" -ne 0 ]; then
    echo "::error::$p 删改上游已有代码（$removed 行），只允许新增 #ifdef __linux__ 块"
    fail=1
  fi
done

# --- 3. 上游子模块必须都在收录清单里 -------------------------------------
while IFS= read -r entry; do
  [ -z "$entry" ] && continue
  mode=${entry%% *}
  path=${entry##*	}
  [ "$mode" = "160000" ] || continue
  if [ -d "$path" ]; then
    continue
  fi
  skip=0
  for p in "${NOT_VENDORED[@]}"; do
    [ "$path" = "$p" ] && skip=1 && break
  done
  if [ $skip -eq 0 ]; then
    echo "::error::上游子模块未收录进本仓库：$path"
    fail=1
  fi
done < <(git ls-tree -r "$UPSTREAM_REF" -- third-party/ packaging/linux/flatpak/deps/)

if [ $fail -ne 0 ]; then
  echo "边界检查失败：以上文件不属于文本输入改动范围。" >&2
  exit 1
fi
echo "边界检查通过（上游 $UPSTREAM_REF）"
