"""
tests/test_catalogo.py
-------------------------
Pruebas de la lógica de negocio de la pinturería: que el cálculo de litros sea correcto, que
la combinación de envases elegida sea la más barata posible, y que cuando falta stock se
encuentre una alternativa de otra marca.
"""
from __future__ import annotations

from retrieval.catalogo import Catalogo, armar_combinacion_envases, calcular_litros_necesarios


def test_busqueda_por_criterios_encuentra_producto():
    cat = Catalogo()
    resultados = cat.buscar(linea="Latex Interior", color="Blanco", marca="ColorMax", acabado="Mate")
    assert len(resultados) >= 1
    assert all(p.marca == "ColorMax" for p in resultados)


def test_calculo_de_litros_con_dos_manos():
    cat = Catalogo()
    producto = cat.buscar(linea="Latex Interior", marca="ColorMax", acabado="Mate", color="Blanco")[0]
    litros = calcular_litros_necesarios(m2=40, producto=producto, manos=2)
    # (40 m2 * 2 manos) / 10 m2 por litro = 8 litros
    assert litros == 8.0


def test_calculo_de_litros_impermeabilizante_no_multiplica_por_manos():
    cat = Catalogo()
    producto = cat.buscar(linea="Impermeabilizante Techos", marca="ColorMax")[0]
    litros = calcular_litros_necesarios(m2=60, producto=producto, manos=2)
    # el rendimiento del impermeabilizante YA incluye las 2 manos -> no se multiplica de nuevo
    assert litros == 60 / producto.rendimiento_m2_por_litro


def test_combinacion_de_envases_elige_la_mas_barata_no_la_mas_grande():
    cat = Catalogo()
    producto = cat.buscar(linea="Latex Interior", marca="ColorMax", acabado="Mate", color="Blanco")[0]
    variantes = cat.variantes_de_presentacion(producto)  # 20L(stock4), 4L(stock0), 1L(stock25)

    items, litros_cubiertos, alcanzo = armar_combinacion_envases(variantes, litros_necesarios=8.0)

    assert alcanzo is True
    assert litros_cubiertos == 8.0
    costo_total = sum(it.precio_subtotal for it in items)
    # 8x1L ($52.000) tiene que ganarle a comprar 1x20L ($98.000)
    assert costo_total == 52000.0


def test_producto_sin_stock_en_ninguna_presentacion_no_alcanza():
    cat = Catalogo()
    producto = cat.buscar(linea="Esmalte Sintetico", marca="Recubrimax", color="Blanco")[0]
    assert producto.stock == 0

    variantes = cat.variantes_de_presentacion(producto)
    items, litros_cubiertos, alcanzo = armar_combinacion_envases(variantes, litros_necesarios=2.0)
    assert alcanzo is False


def test_alternativas_encuentra_otra_marca_con_stock():
    cat = Catalogo()
    producto = cat.buscar(linea="Esmalte Sintetico", marca="Recubrimax", color="Blanco")[0]
    alternativas = cat.alternativas(producto)

    assert len(alternativas) >= 1
    assert all(alt.marca != "Recubrimax" for alt in alternativas)
    assert all(alt.stock > 0 for alt in alternativas)
    assert all(alt.linea == producto.linea and alt.uso == producto.uso for alt in alternativas)
