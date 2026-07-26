"""
orquestacion/pipeline.py
---------------------------
Coordina el prompt (las instrucciones + los datos) con el LLM para redactar el texto final
de la cotización. Importante: el LLM SOLO redacta, nunca calcula — los litros, las
cantidades de envases y los precios ya vienen calculados por retrieval/catalogo.py antes de
llegar acá.
"""
from __future__ import annotations

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from orquestacion.llm_provider import MifeLLM

SYSTEM_INSTRUCTIONS = """Sos el asistente interno de Pinturería MIFE que ayuda a los
vendedores a armar cotizaciones para sus clientes. Redactás un mensaje breve y claro que el
vendedor le pueda pasar directo al cliente. Usá ÚNICAMENTE los números y datos del CONTEXTO
(ya vienen calculados, no los recalcules ni los cambies). Si el contexto menciona que se usó
un producto alternativo por falta de stock del original, aclaralo con buena onda. Si el
contexto incluye una recomendación extra (ej. sumar fijador), mencionala como sugerencia."""

COTIZACION_PROMPT = PromptTemplate.from_template(
    """{system}

CONTEXTO:
{contexto}

PEDIDO: {pedido}

RESPUESTA:"""
)


class CotizacionPipeline:
    def __init__(self, llm: MifeLLM):
        self.llm = llm
        self.chain = COTIZACION_PROMPT | self.llm | StrOutputParser()

    def run(self, pedido: str, contexto: str) -> str:
        return self.chain.invoke({"system": SYSTEM_INSTRUCTIONS, "contexto": contexto, "pedido": pedido})
