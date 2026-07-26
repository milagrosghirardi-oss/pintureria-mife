"""
tests/test_agente.py
-----------------------
Pruebas del agente completo: confirman que los 3 caminos de decisión funcionan (cotizar
directo, pedir información faltante, y usar un producto alternativo cuando no hay stock).
"""
from __future__ import annotations

from agente.graph import get_agent
from agente.interpretar import interpretar_pedido


def test_interpretar_extrae_todos_los_campos_de_un_pedido_completo():
    pedido, faltantes = interpretar_pedido(
        "El cliente quiere pintar un living de 40m2, color blanco, prefiere ColorMax, 2 manos"
    )
    assert pedido.linea == "Latex Interior"
    assert pedido.color == "Blanco"
    assert pedido.marca == "ColorMax"
    assert pedido.metros_cuadrados == 40.0
    assert pedido.manos == 2
    assert faltantes == []


def test_interpretar_detecta_campos_faltantes():
    _, faltantes = interpretar_pedido("Necesita pintar una reja de hierro")
    assert len(faltantes) == 2  # faltan m2 y color


def test_agente_cotiza_directo_cuando_tiene_toda_la_informacion():
    agent = get_agent()
    estado = agent.invoke({"mensaje_original": "Pintar un living de 40m2, blanco, ColorMax, 2 manos"})
    assert estado["necesita_aclaracion"] is False
    assert "52,000" in estado["respuesta_final"] or "52000" in estado["respuesta_final"]


def test_agente_pide_informacion_cuando_falta_algo():
    agent = get_agent()
    estado = agent.invoke({"mensaje_original": "Necesita pintar una reja de hierro"})
    assert estado["necesita_aclaracion"] is True
    assert "metros cuadrados" in estado["respuesta_final"]


def test_agente_usa_alternativa_cuando_no_hay_stock():
    agent = get_agent()
    estado = agent.invoke(
        {"mensaje_original": "Quiere esmalte sintetico brillante blanco marca Recubrimax para 15m2 de reja"}
    )
    assert estado["necesita_aclaracion"] is False
    assert estado["usando_alternativa"] is True
    assert estado["producto_elegido"].marca != "Recubrimax"
    assert "reemplazo" in estado["respuesta_final"].lower()


def test_agente_avisa_cuando_no_hay_stock_de_ninguna_marca():
    """Caso límite: ni el producto pedido ni ninguna alternativa tienen stock."""
    agent = get_agent()
    # Buscamos un caso realista: pedimos un color/linea que exista pero fuerce 0 en todas las marcas.
    # Con el catálogo actual no hay ningún caso así a propósito (siempre hay alguna alternativa),
    # así que probamos directamente el nodo con un estado simulado.
    from agente.graph import node_generar_respuesta

    estado_simulado = {
        "pedido": interpretar_pedido("pintar una pared de 10m2 blanco")[0],
        "producto_elegido": None,
        "producto_original_nombre": "Recubrimax Latex Interior",
    }
    resultado = node_generar_respuesta(estado_simulado)
    assert "no hay stock" in resultado["respuesta_final"].lower()
