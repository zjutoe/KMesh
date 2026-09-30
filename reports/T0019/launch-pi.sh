#!/usr/bin/env bash
# Preparation only: invoking this from a real terminal publishes/starts T0019.
set -eu

if [ "$#" -gt 1 ]; then
    printf 'Usage: bash %s [--resume]\n' "$0" >&2
    exit 2
fi

export PI_CODING_AGENT_DIR=/home/mye/data/kmesh-T0019-preparation-cwn8wlo4/launch-pi
export CUDA_VISIBLE_DEVICES=
export PYTHONDONTWRITEBYTECODE=1
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
export http_proxy=http://127.0.0.1:8888 https_proxy=http://127.0.0.1:8888
export HTTP_PROXY=http://127.0.0.1:8888 HTTPS_PROXY=http://127.0.0.1:8888
export NO_PROXY=localhost,127.0.0.1,::1 no_proxy=localhost,127.0.0.1,::1
unset PYTHONPATH

case "${1-}" in
    '')
        exec /home/mye/.local/bin/codinator pi /home/mye/src/llm/KMesh/reports/T0019/task.json
        ;;
    --resume)
        exec /home/mye/.local/bin/codinator pi T0019-motif-candidate-audit --resume
        ;;
    *)
        printf 'Usage: bash %s [--resume]\n' "$0" >&2
        exit 2
        ;;
esac
