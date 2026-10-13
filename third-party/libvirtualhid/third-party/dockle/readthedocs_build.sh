#!/usr/bin/env bash
set -euo pipefail

dockle_dir="$(cd -- "${DOCKLE_DIR:-$(dirname -- "${BASH_SOURCE[0]}")}" && pwd -P)"
project_dir="$(pwd -P)"
environment_name="${READTHEDOCS_VERSION:-dockle-docs}"
environment_file="${dockle_dir}/environment.yml"
uses_doxygen="$(
  python -c \
    'import tomllib; config = tomllib.load(open("dockle.toml", "rb")); print(any(t.get("framework") == "doxygen" for t in config["targets"]))'
)"

if [[ "${uses_doxygen}" == "True" ]]; then
  echo "Creating the Dockle documentation environment from ${environment_file}"
  conda env create --quiet --name "${environment_name}" --file "${environment_file}"
  environment_run=(conda run --no-capture-output --name "${environment_name}")
else
  echo "Using the Read the Docs Python environment; this project has no Doxygen target"
  # Bash 3.2 treats an empty array as unset under nounset; env is a passthrough.
  environment_run=(env)
fi

npm --prefix "${dockle_dir}" ci --ignore-scripts
npm --prefix "${dockle_dir}" run build

uv_run=("${environment_run[@]}" uv)
python_executable="$("${environment_run[@]}" python -c 'import sys; print(sys.executable)')"
"${uv_run[@]}" sync --project "${dockle_dir}" --locked --all-extras --no-dev --python "${python_executable}"
dockle_run=(
  "${uv_run[@]}" run --project "${dockle_dir}" --locked --all-extras --no-dev --no-sync
)

docs_selection="$(
  python - <<'PY'
import tomllib
from pathlib import Path

path = Path("pyproject.toml")
config = tomllib.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
options = []
if "docs" in config.get("dependency-groups", {}):
    options.extend((
        "--group",
        "docs",
    ))
if "docs" in config.get("project", {}).get("optional-dependencies", {}):
    options.extend((
        "--extra",
        "docs",
    ))
print(" ".join(options))
PY
)"

if [[ -n "${docs_selection}" ]]; then
  echo "Installing the locked project runtime and documentation dependencies"
  read -r -a docs_options <<< "${docs_selection}"
  docs_requirements="$(mktemp)"
  trap 'rm -f "${docs_requirements}"' EXIT
  "${uv_run[@]}" export \
    --quiet \
    --project "${project_dir}" \
    --locked \
    --no-dev \
    "${docs_options[@]}" \
    --no-emit-project \
    --no-emit-package lizardbyte-dockle \
    --python "${python_executable}" \
    --format requirements.txt \
    --output-file "${docs_requirements}"
  "${uv_run[@]}" pip install \
    --python "${dockle_dir}/.venv/bin/python" \
    --requirement "${docs_requirements}"
  rm -f "${docs_requirements}"
  trap - EXIT
elif [[ -f docs/requirements.txt ]]; then
  "${uv_run[@]}" pip install \
    --python "${dockle_dir}/.venv/bin/python" \
    --requirement docs/requirements.txt
fi

if [[ -f readthedocs_pre_build.sh ]]; then
  chmod +x readthedocs_pre_build.sh
  ./readthedocs_pre_build.sh
fi

"${dockle_run[@]}" python -m dockle check
"${dockle_run[@]}" python -m dockle build

if [[ -f readthedocs_post_build.sh ]]; then
  chmod +x readthedocs_post_build.sh
  ./readthedocs_post_build.sh
fi

mkdir -p "${READTHEDOCS_OUTPUT}html/"
cp -r _site/. "${READTHEDOCS_OUTPUT}html/"
