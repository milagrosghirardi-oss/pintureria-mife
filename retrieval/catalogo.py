"""
retrieval/catalogo.py
------------------------
El catálogo estructurado (las tablas CSV) y toda la lógica de negocio de una pinturería:
cuántos litros hacen falta para cubrir una superficie, qué combinación de envases conviene
comprar, y qué producto ofrecer como reemplazo si no hay stock del pedido original.

Decisión importante: estos cálculos los hace código Python normal (matemática exacta), NO
se le pide al LLM que "calcule" nada — un modelo de lenguaje puede equivocarse en cuentas, así
que las cuentas las hace código determinístico y el LLM solo redacta el resultado en texto
para el vendedor. Esto es clave para que las cotizaciones sean confiables.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CATALOGO_PINTURAS = Path(__file__).resolve().parent.parent / "data" / "catalogo" / "catalogo_pinturas.csv"
DEFAULT_CATALOGO_ACCESORIOS = Path(__file__).resolve().parent.parent / "data" / "catalogo" / "catalogo_accesorios.csv"

MANOS_POR_DEFECTO = 2


@dataclass
class Producto:
    sku: str
    marca: str
    linea: str
    acabado: str
    uso: str
    color: str
    rendimiento_m2_por_litro: float
    manos_incluidas_en_rendimiento: bool
    presentacion_litros: float
    precio_ars: float
    stock: int


@dataclass
class Accesorio:
    sku: str
    producto: str
    uso_recomendado: str
    precio_ars: float
    stock: int


@dataclass
class ItemCotizado:
    producto: Producto
    cantidad_envases: int
    litros_totales: float
    precio_subtotal: float


def _norm(valor: str) -> str:
    return (valor or "").strip().lower()


def cargar_pinturas(path: str | Path = DEFAULT_CATALOGO_PINTURAS) -> list[Producto]:
    productos = []
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            productos.append(
                Producto(
                    sku=row["sku"],
                    marca=row["marca"],
                    linea=row["linea"],
                    acabado=row["acabado"],
                    uso=row["uso"],
                    color=row["color"],
                    rendimiento_m2_por_litro=float(row["rendimiento_m2_por_litro"]),
                    manos_incluidas_en_rendimiento=_norm(row["manos_incluidas_en_rendimiento"]) == "si",
                    presentacion_litros=float(row["presentacion_litros"]),
                    precio_ars=float(row["precio_ars"]),
                    stock=int(row["stock"]),
                )
            )
    return productos


def cargar_accesorios(path: str | Path = DEFAULT_CATALOGO_ACCESORIOS) -> list[Accesorio]:
    accesorios = []
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            accesorios.append(
                Accesorio(
                    sku=row["sku"],
                    producto=row["producto"],
                    uso_recomendado=row["uso_recomendado"],
                    precio_ars=float(row["precio_ars"]),
                    stock=int(row["stock"]),
                )
            )
    return accesorios


class Catalogo:
    def __init__(
        self,
        path_pinturas: str | Path = DEFAULT_CATALOGO_PINTURAS,
        path_accesorios: str | Path = DEFAULT_CATALOGO_ACCESORIOS,
    ):
        self.pinturas = cargar_pinturas(path_pinturas)
        self.accesorios = cargar_accesorios(path_accesorios)

    def buscar(
        self, linea: str | None = None, uso: str | None = None, color: str | None = None,
        marca: str | None = None, acabado: str | None = None,
    ) -> list[Producto]:
        """Busca productos que matcheen los criterios dados (los que sean None no filtran)."""
        resultado = self.pinturas
        if linea:
            resultado = [p for p in resultado if _norm(linea) in _norm(p.linea)]
        if uso:
            resultado = [p for p in resultado if _norm(uso) in _norm(p.uso)]
        if color:
            resultado = [p for p in resultado if _norm(color) in _norm(p.color)]
        if marca:
            resultado = [p for p in resultado if _norm(marca) == _norm(p.marca)]
        if acabado:
            resultado = [p for p in resultado if _norm(acabado) == _norm(p.acabado)]
        return resultado

    def variantes_de_presentacion(self, producto: Producto) -> list[Producto]:
        """Todas las presentaciones (tamaños de envase) del MISMO producto exacto (misma
        marca/línea/acabado/color), ordenadas de mayor a menor litros."""
        variantes = [
            p for p in self.pinturas
            if p.marca == producto.marca and p.linea == producto.linea
            and p.acabado == producto.acabado and p.color == producto.color
        ]
        return sorted(variantes, key=lambda p: p.presentacion_litros, reverse=True)

    def alternativas(self, producto: Producto) -> list[Producto]:
        """Productos equivalentes (mismo tipo, mismo uso, terminación igual, sin stock del
        original) de OTRA marca, con stock disponible. Ordenados por rendimiento (el que
        más cerca esté del original primero)."""
        candidatos = [
            p for p in self.pinturas
            if p.linea == producto.linea and p.uso == producto.uso
            and p.acabado == producto.acabado and p.color == producto.color
            and p.marca != producto.marca and p.stock > 0
        ]
        return sorted(candidatos, key=lambda p: abs(p.rendimiento_m2_por_litro - producto.rendimiento_m2_por_litro))


def calcular_litros_necesarios(m2: float, producto: Producto, manos: int = MANOS_POR_DEFECTO) -> float:
    """La cuenta central de cualquier cotización de pintura."""
    if producto.manos_incluidas_en_rendimiento:
        return m2 / producto.rendimiento_m2_por_litro
    return (m2 * manos) / producto.rendimiento_m2_por_litro


def armar_combinacion_envases(
    variantes: list[Producto], litros_necesarios: float
) -> tuple[list[ItemCotizado], float, bool]:
    """Elige qué envases comprar para cubrir los litros necesarios al MENOR COSTO posible,
    respetando el stock disponible de cada presentación.

    Prueba combinaciones de cantidades para cada tamaño de envase disponible y se queda con
    la de menor costo total que cubra lo necesario (si ninguna alcanza a cubrirlo del todo
    por falta de stock, devuelve la mejor cobertura posible comprando todo lo disponible, y
    lo marca como "no alcanzó" para que el agente busque una marca alternativa).

    Es una búsqueda exhaustiva acotada (no una optimización matemática avanzada), pero para
    la cantidad de tamaños de envase que maneja una pinturería (típicamente 2 a 4) es rápida
    y da el resultado correcto, a diferencia de un atajo "greedy" que puede elegir mal cuando
    hay saltos grandes entre tamaños (ej. 1L, 4L, 20L).
    """
    import itertools
    import math

    variantes_con_stock = [v for v in variantes if v.stock > 0]
    if not variantes_con_stock or litros_necesarios <= 0:
        return [], 0.0, False

    rangos = [
        range(0, min(v.stock, math.ceil(litros_necesarios / v.presentacion_litros) + 1) + 1)
        for v in variantes_con_stock
    ]

    mejor_combo, mejor_costo, mejor_litros = None, None, 0.0
    for combinacion in itertools.product(*rangos):
        litros_totales = sum(cant * v.presentacion_litros for cant, v in zip(combinacion, variantes_con_stock))
        if litros_totales + 0.001 < litros_necesarios:
            continue
        costo_total = sum(cant * v.precio_ars for cant, v in zip(combinacion, variantes_con_stock))
        if mejor_costo is None or costo_total < mejor_costo:
            mejor_combo, mejor_costo, mejor_litros = combinacion, costo_total, litros_totales

    if mejor_combo is not None:
        items = [
            ItemCotizado(producto=v, cantidad_envases=cant, litros_totales=cant * v.presentacion_litros, precio_subtotal=cant * v.precio_ars)
            for cant, v in zip(mejor_combo, variantes_con_stock)
            if cant > 0
        ]
        return items, mejor_litros, True

    # Ninguna combinación alcanza a cubrir lo necesario -> comprar todo el stock disponible
    # (mejor esfuerzo) y avisar que no alcanzó, para que el agente busque una marca alternativa.
    items = [
        ItemCotizado(producto=v, cantidad_envases=v.stock, litros_totales=v.stock * v.presentacion_litros, precio_subtotal=v.stock * v.precio_ars)
        for v in variantes_con_stock
    ]
    litros_cubiertos = sum(it.litros_totales for it in items)
    return items, litros_cubiertos, False
