"""
adaptadores_mcp/stock_server.py
-----------------------------------
Servidor MCP (protocolo real, SDK oficial `mcp`) que expone el stock de MIFE como
herramientas seguras. El agente no lee el catálogo directo — le pide a este servidor que lo
haga, con guardrails: el SKU tiene que tener el formato exacto de MIFE (empieza con "MIFE-"),
cualquier otra cosa se rechaza antes de tocar los datos.
"""
from __future__ import annotations

import re

from mcp.server.fastmcp import FastMCP

from retrieval.catalogo import Catalogo

SKU_RE = re.compile(r"^MIFE-[A-Z0-9-]+$")

mcp = FastMCP("mife-stock-adapter")
_catalogo = Catalogo()


@mcp.tool()
def consultar_stock(sku: str) -> dict:
    """Consulta el stock disponible de un SKU de MIFE (formato MIFE-XX-XX-...)."""
    sku = sku.strip().upper()
    if not SKU_RE.match(sku):
        return {"error": "formato_invalido", "mensaje": "El SKU debe tener el formato MIFE-..."}

    producto = next((p for p in _catalogo.pinturas if p.sku == sku), None)
    if producto is None:
        return {"error": "no_encontrado", "mensaje": "No se encontró un producto con ese SKU."}

    return {
        "sku": producto.sku, "marca": producto.marca, "linea": producto.linea,
        "presentacion_litros": producto.presentacion_litros, "stock": producto.stock,
        "disponible": producto.stock > 0,
    }


@mcp.tool()
def buscar_equivalencia(sku: str) -> dict:
    """Busca un producto equivalente de otra marca cuando el SKU pedido no tiene stock."""
    sku = sku.strip().upper()
    if not SKU_RE.match(sku):
        return {"error": "formato_invalido", "mensaje": "El SKU debe tener el formato MIFE-..."}

    producto = next((p for p in _catalogo.pinturas if p.sku == sku), None)
    if producto is None:
        return {"error": "no_encontrado", "mensaje": "No se encontró un producto con ese SKU."}

    alternativas = _catalogo.alternativas(producto)
    if not alternativas:
        return {"error": "sin_alternativas", "mensaje": "No hay equivalentes con stock de otra marca."}

    mejor = alternativas[0]
    return {"sku_equivalente": mejor.sku, "marca": mejor.marca, "stock": mejor.stock}


if __name__ == "__main__":
    mcp.run(transport="stdio")
