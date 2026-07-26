"""
agente/session.py
--------------------
Envuelve al agente con medición de latencia, costo estimado y el chequeo de anclaje numérico
(Pilar de observabilidad), para que main.py no tenga que preocuparse por esto.
"""
from __future__ import annotations

import time

from agente.graph import get_agent
from observabilidad.metrics import (
    InferenceMetric,
    chequear_anclaje_numerico,
    estimar_costo,
    medir_latencia,
    registrar_metrica,
)
from orquestacion.llm_provider import get_llm

_llm = get_llm()


def cotizar(mensaje: str) -> dict:
    agent = get_agent()
    with medir_latencia() as timer:
        estado = agent.invoke({"mensaje_original": mensaje})

    respuesta = estado.get("respuesta_final", "")
    contexto_aprox = str(estado.get("items_cotizados", "")) + str(estado.get("litros_necesarios", ""))
    anclaje = chequear_anclaje_numerico(respuesta, contexto_aprox) if not estado.get("necesita_aclaracion") else 1.0

    prompt_tokens = _llm.get_num_tokens(mensaje)
    output_tokens = _llm.get_num_tokens(respuesta)
    costo = estimar_costo(_llm.provider, prompt_tokens, output_tokens)

    registrar_metrica(
        InferenceMetric(
            timestamp=time.time(),
            latencia_ms=round(timer["ms"], 1),
            provider=_llm.provider,
            necesito_aclaracion=bool(estado.get("necesita_aclaracion", False)),
            uso_alternativa=bool(estado.get("usando_alternativa", False)),
            numeros_anclados_pct=anclaje,
            costo_usd_estimado=costo,
        )
    )
    return estado
