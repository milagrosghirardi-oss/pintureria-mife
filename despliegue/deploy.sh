#!/bin/bash
# despliegue/deploy.sh
# Uso: ./deploy.sh local   (docker compose)
#      ./deploy.sh k8s --dry-run   (valida manifiestos)
set -euo pipefail
MODO="${1:-local}"
DRY_RUN="${2:-}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

case "$MODO" in
  local)
    cd "$ROOT_DIR/despliegue" && docker compose up --build
    ;;
  k8s)
    ARGS=""
    [ "$DRY_RUN" == "--dry-run" ] && ARGS="--dry-run=client"
    kubectl apply -f "$ROOT_DIR/despliegue/k8s.yaml" $ARGS
    ;;
  *)
    echo "Uso: $0 [local|k8s] [--dry-run]"; exit 1 ;;
esac
