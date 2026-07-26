"""
main.py
---------
CLI para que un vendedor le tipee el pedido del cliente y reciba la cotización.

Uso:
    python -m retrieval.ingest --docs data/docs_ejemplo   # (solo la primera vez)
    python main.py
"""
from __future__ import annotations

import sys

from agente.session import cotizar
from observabilidad.metrics import resumir_metricas
from orquestacion.llm_provider import get_llm

BANNER = """
==================================================
  Asistente de Cotizaciones — Pintureria MIFE
==================================================
Escribi el pedido del cliente (o "salir", o "metricas").
"""


def main():
    llm = get_llm()
    print(BANNER)
    print(f"[modo LLM: {llm.provider}]\n")
    while True:
        try:
            mensaje = input("Vendedor: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nChau!")
            sys.exit(0)
        if not mensaje:
            continue
        if mensaje.lower() in {"salir", "exit"}:
            break
        if mensaje.lower() == "metricas":
            import json
            print(json.dumps(resumir_metricas(), indent=2, ensure_ascii=False))
            continue

        estado = cotizar(mensaje)
        print(f"\nAsistente: {estado['respuesta_final']}\n")


if __name__ == "__main__":
    main()
