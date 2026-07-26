"""
agente/state.py
------------------
El "estado" es la información que va viajando por todos los pasos del grafo (cada paso lee lo
que necesita y agrega lo que calculó).
"""
from __future__ import annotations

from typing import TypedDict


class VentaState(TypedDict, total=False):
    mensaje_original: str
    texto: str

    pedido: object  # Pedido (de agente/interpretar.py)
    faltantes: list[str]

    producto_elegido: object  # Producto | None
    usando_alternativa: bool
    producto_original_nombre: str | None

    items_cotizados: list
    litros_necesarios: float
    litros_cubiertos: float
    alcanza_stock: bool

    contexto_docs: str
    respuesta_final: str
    necesita_aclaracion: bool
