# Asistente de Cotizaciones — Pinturería MIFE

Asistente interno para vendedores de una pinturería ficticia: recibe el pedido de un cliente
(texto, o audio ya transcripto), busca el producto correcto en el catálogo técnico, calcula
cuántos litros y qué envases hacen falta, arma el precio, y si no hay stock busca un
reemplazo automático de otra marca. Si falta información, en vez de inventar, le pregunta al
vendedor.

## Arquitectura

```
mensaje (texto/audio) -> transcribir -> interpretar pedido -> buscar producto
                                                                    |
                                          ¿alcanza el stock? --no--> buscar alternativa
                                                |sí                        |
                                                v                          v
                                          calcular cotización (litros, envases, precio)
                                                |
                                          redactar respuesta (LLM + tips de los manuales)
```

- `retrieval/` — búsqueda híbrida sobre los manuales técnicos (ChromaDB + BM25) y el catálogo
  estructurado (`catalogo.py`: búsqueda por criterios, cálculo de litros, combinación de
  envases al menor costo, y búsqueda de equivalencias).
- `ranking/` — reordena los resultados de búsqueda antes de mandarlos al LLM.
- `orquestacion/` — LLM intercambiable (mock/Claude) + el pipeline que arma el prompt final.
- `agente/` — el grafo de decisión (LangGraph): interpreta, busca, calcula, decide si cotizar
  o pedir más información.
- `adaptadores_mcp/` — protocolo MCP real para consultar stock de forma segura, y el
  adaptador de transcripción de audio (mock, con la integración real documentada como
  siguiente paso).
- `observabilidad/` — métricas (latencia, costo, % de cotizaciones que necesitaron
  aclaración o reemplazo, anclaje numérico como proxy de alucinación) + Arize Phoenix.
- `despliegue/` — Docker, Kubernetes, script de despliegue.

## Quickstart

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python -m retrieval.ingest --docs data/docs_ejemplo
python main.py
```

Probá pedidos como:
- `"Pintar un living de 40m2, blanco, ColorMax"` → cotiza directo.
- `"Necesita pintar una reja de hierro"` → pide los datos que faltan.
- `"Esmalte sintetico blanco Recubrimax para 15m2"` → busca equivalencia (Recubrimax no
  tiene stock en el catálogo de ejemplo).

## Tests

```bash
pytest tests/ -v
```

## LLM real (Claude)

```bash
export LLM_PROVIDER=claude
export ANTHROPIC_API_KEY=sk-...
python main.py
```

## Decisiones de diseño (resumen — ver docs/ARQUITECTURA.md para el detalle)

- **La interpretación del pedido usa reglas simples, no el LLM**: el vocabulario es chico y
  conocido (3 marcas, un puñado de tipos de producto), así que reglas explícitas son más
  predecibles que confiarle esta parte al modelo de lenguaje.
- **Los cálculos (litros, envases, precio) los hace código Python, nunca el LLM**: evita que
  una cotización tenga un error de matemática por una alucinación del modelo.
- **Cuando falta información, el asistente le pregunta al vendedor** (no responde "no sé" ni
  deriva a otra persona) — es un asistente interno, el humano ya está en la conversación.
