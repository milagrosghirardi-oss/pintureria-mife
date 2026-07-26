"""
agente/api.py
----------------
Expone el asistente como API REST, para que se pueda integrar a una app interna de MIFE (o
probarlo con curl/Postman).

Correr local: uvicorn agente.api:app --port 8000
"""
from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from agente.session import cotizar
from observabilidad.metrics import resumir_metricas

app = FastAPI(title="MIFE - Asistente de Cotizaciones")


class PedidoRequest(BaseModel):
    mensaje: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/cotizar")
def cotizar_endpoint(req: PedidoRequest):
    estado = cotizar(req.mensaje)
    return {
        "respuesta": estado.get("respuesta_final", ""),
        "necesita_aclaracion": bool(estado.get("necesita_aclaracion", False)),
        "uso_alternativa": bool(estado.get("usando_alternativa", False)),
    }


@app.get("/metrics")
def metrics():
    return resumir_metricas()
