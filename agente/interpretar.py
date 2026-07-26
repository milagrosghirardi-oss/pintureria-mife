"""
agente/interpretar.py
------------------------
Convierte el texto libre del vendedor (lo que escribió o lo que dijo el cliente, ya
transcripto) en datos ordenados: qué tipo de producto, para qué superficie, qué color,
cuántos metros cuadrados.

Decisión de diseño: esto NO se lo pedimos al LLM — lo hacemos con reglas explícitas (buscar
palabras clave, buscar números). ¿Por qué? Porque acá el vocabulario es chico y conocido (3
marcas, un puñado de colores y tipos de producto), así que reglas simples son más
predecibles y más fáciles de auditar que confiar en que el LLM "entienda" bien siempre. No
todo necesita inteligencia artificial — a veces una regla simple es la herramienta correcta.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_LINEAS_POR_PALABRA_CLAVE = [
    (r"\btecho|gotea|filtra|filtracion\b", "Impermeabilizante Techos", "Exterior"),
    (r"\breja|porton|metal|hierro|antioxido\b", "Esmalte Sintetico", "Metal/Madera"),
    (r"\bmadera|puerta|mueble|zocalo\b", "Esmalte Sintetico", "Metal/Madera"),
    (r"\bfachada|frente|exterior\b", "Latex Exterior", "Exterior"),
    (r"\binterior|living|dormitorio|cuarto|habitacion|pared\b", "Latex Interior", "Interior"),
]

_COLORES_CONOCIDOS = ["blanco", "beige", "gris perla", "gris", "negro", "incoloro"]
_MARCAS_CONOCIDAS = ["colormax", "recubrimax", "tonosur"]

_M2_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:m2|m²|metros?\s*cuadrados?)", re.IGNORECASE)
_MANOS_RE = re.compile(r"\b(\d+|una|dos|tres)\s*manos?\b", re.IGNORECASE)
_PALABRA_A_NUMERO = {"una": 1, "dos": 2, "tres": 3}


@dataclass
class Pedido:
    texto_original: str
    linea: str | None = None
    uso: str | None = None
    color: str | None = None
    marca: str | None = None
    acabado: str | None = None
    metros_cuadrados: float | None = None
    manos: int = 2


def interpretar_pedido(texto: str) -> tuple[Pedido, list[str]]:
    """Devuelve (pedido interpretado, lista de cosas que faltan para poder cotizar)."""
    texto_lower = texto.lower()
    pedido = Pedido(texto_original=texto)

    for patron, linea, uso in _LINEAS_POR_PALABRA_CLAVE:
        if re.search(patron, texto_lower):
            pedido.linea = linea
            pedido.uso = uso
            break

    for color in _COLORES_CONOCIDOS:
        if color in texto_lower:
            pedido.color = color.title()
            break

    for marca in _MARCAS_CONOCIDAS:
        if marca in texto_lower:
            pedido.marca = marca.replace("colormax", "ColorMax").replace("recubrimax", "Recubrimax").replace("tonosur", "TonoSur")
            break

    if "mate" in texto_lower:
        pedido.acabado = "Mate"
    elif "satinad" in texto_lower:
        pedido.acabado = "Satinado"
    elif "brillante" in texto_lower:
        pedido.acabado = "Brillante"

    m2_match = _M2_RE.search(texto_lower)
    if m2_match:
        pedido.metros_cuadrados = float(m2_match.group(1).replace(",", "."))

    manos_match = _MANOS_RE.search(texto_lower)
    if manos_match:
        valor = manos_match.group(1)
        pedido.manos = _PALABRA_A_NUMERO.get(valor, int(valor) if valor.isdigit() else 2)

    faltantes = []
    if pedido.linea is None:
        faltantes.append("qué tipo de superficie es (pared interior, fachada, techo, metal o madera)")
    if pedido.metros_cuadrados is None:
        faltantes.append("cuántos metros cuadrados hay que cubrir")
    if pedido.color is None:
        faltantes.append("qué color prefiere el cliente")

    return pedido, faltantes
