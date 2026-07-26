# despliegue/Dockerfile
FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt fastapi "uvicorn[standard]"

COPY retrieval/ ./retrieval/
COPY ranking/ ./ranking/
COPY orquestacion/ ./orquestacion/
COPY agente/ ./agente/
COPY adaptadores_mcp/ ./adaptadores_mcp/
COPY observabilidad/ ./observabilidad/
COPY data/docs_ejemplo/ ./data/docs_ejemplo/
COPY data/catalogo/ ./data/catalogo/

ENV LLM_PROVIDER=mock

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

COPY despliegue/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
