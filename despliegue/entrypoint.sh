#!/bin/sh
set -e
if [ ! -f "/app/data/embedder.pkl" ]; then
  echo "[entrypoint] Indexando documentos..."
  python -m retrieval.ingest --docs /app/data/docs_ejemplo
fi
exec uvicorn agente.api:app --host 0.0.0.0 --port 8000
