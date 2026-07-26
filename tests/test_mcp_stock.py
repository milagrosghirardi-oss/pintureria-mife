"""
tests/test_mcp_stock.py
--------------------------
Prueba el protocolo MCP real: consulta válida, formato inválido bloqueado, y equivalencia.
"""
from __future__ import annotations

import asyncio

from adaptadores_mcp.stock_client import call_tool


def test_consultar_stock_formato_valido():
    resultado = asyncio.run(call_tool("consultar_stock", {"sku": "MIFE-CM-LI-MAT-BLA-1"}))
    assert resultado["disponible"] is True


def test_consultar_stock_rechaza_formato_invalido():
    resultado = asyncio.run(call_tool("consultar_stock", {"sku": "'; DROP TABLE productos;--"}))
    assert resultado["error"] == "formato_invalido"


def test_buscar_equivalencia_encuentra_otra_marca():
    resultado = asyncio.run(call_tool("buscar_equivalencia", {"sku": "MIFE-RM-ES-BRI-BLA-1"}))
    assert resultado["marca"] != "Recubrimax"
    assert resultado["stock"] > 0
