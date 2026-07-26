"""
observabilidad/metrics.py
-----------------------------
Mide lo mismo que pide la consigna: latencia (cuánto tarda), costo por inferencia, y una
señal de "tasa de alucinación" — acá la medimos chequeando que los NÚMEROS que aparecen en la
respuesta final (litros, precios) realmente vinieron del contexto calculado, y no son
"inventados" por el LLM al redactar.
"""
from __future__ import annotations

import json
import re
import statistics
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path

METRICS_PATH = Path(__file__).resolve().parent.parent / "data" / "metrics.jsonl"

PRECIO_INPUT_POR_MILLON = 3.0
PRECIO_OUTPUT_POR_MILLON = 15.0


@dataclass
class InferenceMetric:
    timestamp: float
    latencia_ms: float
    provider: str
    necesito_aclaracion: bool
    uso_alternativa: bool
    numeros_anclados_pct: float
    costo_usd_estimado: float = 0.0
    extra: dict = field(default_factory=dict)


def estimar_costo(provider: str, prompt_tokens: int, output_tokens: int) -> float:
    if provider != "claude":
        return 0.0
    return prompt_tokens / 1_000_000 * PRECIO_INPUT_POR_MILLON + output_tokens / 1_000_000 * PRECIO_OUTPUT_POR_MILLON


def chequear_anclaje_numerico(respuesta: str, contexto: str) -> float:
    """Fracción de números que aparecen en la respuesta y que también están en el contexto
    (si un número de la respuesta no está en el contexto, es una señal de posible invención)."""
    numeros_respuesta = set(re.findall(r"\d+(?:[.,]\d+)?", respuesta))
    if not numeros_respuesta:
        return 1.0
    numeros_contexto = set(re.findall(r"\d+(?:[.,]\d+)?", contexto))
    anclados = sum(1 for n in numeros_respuesta if n in numeros_contexto)
    return anclados / len(numeros_respuesta)


@contextmanager
def medir_latencia():
    data = {}
    inicio = time.perf_counter()
    try:
        yield data
    finally:
        data["ms"] = (time.perf_counter() - inicio) * 1000


def registrar_metrica(metric: InferenceMetric) -> None:
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(METRICS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(metric), ensure_ascii=False) + "\n")


def resumir_metricas() -> dict:
    if not METRICS_PATH.exists():
        return {"mensaje": "Todavía no hay métricas registradas."}
    registros = [json.loads(l) for l in open(METRICS_PATH, encoding="utf-8") if l.strip()]
    if not registros:
        return {"mensaje": "Todavía no hay métricas registradas."}

    return {
        "total_cotizaciones": len(registros),
        "latencia_promedio_ms": round(statistics.mean(r["latencia_ms"] for r in registros), 1),
        "pct_necesito_aclaracion": round(100 * sum(r["necesito_aclaracion"] for r in registros) / len(registros), 1),
        "pct_uso_alternativa": round(100 * sum(r["uso_alternativa"] for r in registros) / len(registros), 1),
        "anclaje_numerico_promedio_pct": round(statistics.mean(r["numeros_anclados_pct"] for r in registros) * 100, 1),
        "costo_total_usd_estimado": round(sum(r["costo_usd_estimado"] for r in registros), 4),
    }
