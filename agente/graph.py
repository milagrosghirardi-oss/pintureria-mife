"""
agente/graph.py
------------------
El grafo cíclico del asistente de cotizaciones. Recorrido típico:

    transcribir -> interpretar -> ¿falta info? --sí--> pedir_aclaracion (FIN)
                                        |no
                                        v
                                  buscar_producto -> ¿no se encontró nada? --sí--> pedir_aclaracion (FIN)
                                        |encontrado
                                        v
                                  calcular_cotizacion -> ¿alcanza el stock? --no--> buscar_alternativa
                                        |sí                                              |
                                        v                                                v
                                  generar_respuesta <---------------------------- (con o sin alternativa)
                                        |
                                       FIN

Diferencia clave con un asistente de cara al público (como el de Mercado Libre de TRV): acá el
"humano" ya está en el medio de la conversación (es el vendedor), así que cuando falta
información la respuesta correcta NO es "no contesto" — es **pedirle al vendedor el dato que
falta**, para que se lo pregunte al cliente y volvamos a intentar.
"""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from adaptadores_mcp.transcripcion import get_transcriptor
from agente.interpretar import interpretar_pedido
from agente.state import VentaState
from orquestacion.llm_provider import get_llm
from orquestacion.pipeline import CotizacionPipeline
from ranking.reranker import HeuristicReranker
from retrieval.catalogo import Catalogo, armar_combinacion_envases, calcular_litros_necesarios
from retrieval.hybrid_search import HybridRetriever

_ACABADO_POR_DEFECTO = {"Latex Interior": "Mate", "Latex Exterior": "Mate", "Esmalte Sintetico": "Brillante", "Esmalte al Agua": "Satinado"}

_catalogo: Catalogo | None = None
_retriever: HybridRetriever | None = None
_reranker = HeuristicReranker()
_llm = get_llm()
_pipeline = CotizacionPipeline(_llm)


def _get_catalogo() -> Catalogo:
    global _catalogo
    if _catalogo is None:
        _catalogo = Catalogo()
    return _catalogo


def _get_retriever() -> HybridRetriever:
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever


def node_transcribir(state: VentaState) -> dict:
    transcriptor = get_transcriptor()
    texto = transcriptor.transcribir(state["mensaje_original"])
    return {"texto": texto}


def node_interpretar(state: VentaState) -> dict:
    pedido, faltantes = interpretar_pedido(state["texto"])
    return {"pedido": pedido, "faltantes": faltantes}


def _falta_informacion(state: VentaState) -> str:
    return "pedir_aclaracion" if state.get("faltantes") else "buscar_producto"


def node_buscar_producto(state: VentaState) -> dict:
    pedido = state["pedido"]
    catalogo = _get_catalogo()
    acabado = pedido.acabado or _ACABADO_POR_DEFECTO.get(pedido.linea)

    candidatos = catalogo.buscar(linea=pedido.linea, uso=pedido.uso, color=pedido.color, marca=pedido.marca, acabado=acabado)
    if not candidatos:
        candidatos = catalogo.buscar(linea=pedido.linea, uso=pedido.uso, color=pedido.color, marca=pedido.marca)

    if not candidatos:
        return {
            "producto_elegido": None,
            "faltantes": [f"no encontramos {pedido.color or ''} {pedido.linea or ''} de la marca pedida en el catálogo — ¿confirmás el color/marca?"],
        }
    return {"producto_elegido": candidatos[0]}


def _se_encontro_producto(state: VentaState) -> str:
    return "pedir_aclaracion" if state.get("producto_elegido") is None else "calcular_cotizacion"


def node_calcular_cotizacion(state: VentaState) -> dict:
    pedido = state["pedido"]
    producto = state["producto_elegido"]
    catalogo = _get_catalogo()

    litros = calcular_litros_necesarios(pedido.metros_cuadrados, producto, manos=pedido.manos)
    variantes = catalogo.variantes_de_presentacion(producto)
    items, litros_cubiertos, alcanza = armar_combinacion_envases(variantes, litros)

    return {
        "litros_necesarios": litros,
        "items_cotizados": items,
        "litros_cubiertos": litros_cubiertos,
        "alcanza_stock": alcanza,
    }


def _alcanza_el_stock(state: VentaState) -> str:
    return "generar_respuesta" if state.get("alcanza_stock") else "buscar_alternativa"


def node_buscar_alternativa(state: VentaState) -> dict:
    producto_original = state["producto_elegido"]
    catalogo = _get_catalogo()
    alternativas = catalogo.alternativas(producto_original)

    if not alternativas:
        return {
            "producto_elegido": None,
            "usando_alternativa": False,
            "producto_original_nombre": f"{producto_original.marca} {producto_original.linea}",
        }

    nueva_alternativa = alternativas[0]
    litros = calcular_litros_necesarios(state["pedido"].metros_cuadrados, nueva_alternativa, manos=state["pedido"].manos)
    variantes = catalogo.variantes_de_presentacion(nueva_alternativa)
    items, litros_cubiertos, alcanza = armar_combinacion_envases(variantes, litros)

    return {
        "producto_elegido": nueva_alternativa,
        "usando_alternativa": True,
        "producto_original_nombre": f"{producto_original.marca} {producto_original.linea}",
        "litros_necesarios": litros,
        "items_cotizados": items,
        "litros_cubiertos": litros_cubiertos,
        "alcanza_stock": alcanza,
    }


def node_generar_respuesta(state: VentaState) -> dict:
    pedido = state["pedido"]

    if state.get("producto_elegido") is None:
        contexto = (
            f"No hay stock disponible de {state.get('producto_original_nombre', 'este producto')} "
            "en ninguna marca equivalente en este momento."
        )
    else:
        items = state["items_cotizados"]
        detalle = ", ".join(f"{it.cantidad_envases}x {it.producto.presentacion_litros}L" for it in items)
        total = sum(it.precio_subtotal for it in items)
        contexto = (
            f"Producto: {state['producto_elegido'].marca} {state['producto_elegido'].linea} "
            f"{state['producto_elegido'].acabado} color {state['producto_elegido'].color}. "
            f"Litros necesarios: {state['litros_necesarios']:.1f}. Envases a llevar: {detalle}. "
            f"Precio total: ${total:,.0f}."
        )
        if state.get("usando_alternativa"):
            contexto += f" NOTA: se usó como reemplazo porque no había stock de {state['producto_original_nombre']}."

        candidatos_tips = _get_retriever().search(pedido.texto_original, top_k=8)
        tips_rankeados = _reranker.rerank(pedido.texto_original, candidatos_tips, top_k=3)
        tips_relevantes = [
            rc.chunk.text for rc in tips_rankeados
            if "sugier" in rc.chunk.text.lower() or "sumar" in rc.chunk.text.lower() or "recomendable" in rc.chunk.text.lower()
        ]
        if tips_relevantes:
            contexto += " Sugerencia adicional: " + " ".join(tips_relevantes)

    respuesta = _pipeline.run(pedido=pedido.texto_original, contexto=contexto)
    return {"respuesta_final": respuesta, "necesita_aclaracion": False}


def node_pedir_aclaracion(state: VentaState) -> dict:
    faltantes = state.get("faltantes", [])
    pedido_texto = "; ".join(faltantes)
    respuesta = f"Para armar la cotización me falta: {pedido_texto}. ¿Se lo podés preguntar al cliente?"
    return {"respuesta_final": respuesta, "necesita_aclaracion": True}


def build_graph():
    graph = StateGraph(VentaState)
    graph.add_node("transcribir", node_transcribir)
    graph.add_node("interpretar", node_interpretar)
    graph.add_node("buscar_producto", node_buscar_producto)
    graph.add_node("calcular_cotizacion", node_calcular_cotizacion)
    graph.add_node("buscar_alternativa", node_buscar_alternativa)
    graph.add_node("generar_respuesta", node_generar_respuesta)
    graph.add_node("pedir_aclaracion", node_pedir_aclaracion)

    graph.set_entry_point("transcribir")
    graph.add_edge("transcribir", "interpretar")
    graph.add_conditional_edges("interpretar", _falta_informacion, {"pedir_aclaracion": "pedir_aclaracion", "buscar_producto": "buscar_producto"})
    graph.add_conditional_edges("buscar_producto", _se_encontro_producto, {"pedir_aclaracion": "pedir_aclaracion", "calcular_cotizacion": "calcular_cotizacion"})
    graph.add_conditional_edges("calcular_cotizacion", _alcanza_el_stock, {"generar_respuesta": "generar_respuesta", "buscar_alternativa": "buscar_alternativa"})
    graph.add_edge("buscar_alternativa", "generar_respuesta")
    graph.add_edge("generar_respuesta", END)
    graph.add_edge("pedir_aclaracion", END)

    return graph.compile()


_compiled = None


def get_agent():
    global _compiled
    if _compiled is None:
        _compiled = build_graph()
    return _compiled
