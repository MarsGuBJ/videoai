#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL_DIR="${ROOT_DIR}/infra/model_repository/arcface_mbf/1"
MODEL_PATH="${MODEL_DIR}/model.onnx"
MODEL_URL="${MODEL_URL:-https://hf-mirror.com/deepghs/insightface/resolve/main/buffalo_s/w600k_mbf.onnx}"
EXPECTED_SHA256="${EXPECTED_SHA256:-9cc6e4a75f0e2bf0b1aed94578f144d15175f357bdc05e815e5c4a02b319eb4f}"

mkdir -p "${MODEL_DIR}"
curl -L --fail --retry 3 --retry-delay 2 -o "${MODEL_PATH}.tmp" "${MODEL_URL}"

actual_sha256="$(sha256sum "${MODEL_PATH}.tmp" | awk '{print $1}')"
if [[ "${actual_sha256}" != "${EXPECTED_SHA256}" ]]; then
  rm -f "${MODEL_PATH}.tmp"
  echo "sha256 mismatch for ${MODEL_URL}" >&2
  echo "expected: ${EXPECTED_SHA256}" >&2
  echo "actual:   ${actual_sha256}" >&2
  exit 1
fi

mv "${MODEL_PATH}.tmp" "${MODEL_PATH}"
echo "Downloaded ${MODEL_PATH}"

