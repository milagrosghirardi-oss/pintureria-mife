# Decisiones Arquitectónicas — Asistente MIFE

## Por qué la interpretación del pedido no usa LLM

El agente de TRV (proyecto hermano de este) usa el LLM para razonar sobre texto libre. Acá
decidimos distinto para `agente/interpretar.py`: el universo de valores posibles es chico y
cerrado (3 marcas, ~8 tipos de producto, un puñado de colores) — un conjunto de reglas
explícitas (buscar palabras clave, buscar números con regex) es más predecible, más fácil de
auditar, y no depende de la calidad del LLM (que en este demo corre en modo simulado). Si en
el futuro el vocabulario crece mucho (muchas más marcas, sinónimos raros), ahí sí valdría la
pena pasar esta parte a un LLM real.

## Por qué los cálculos nunca los hace el LLM

`retrieval/catalogo.py` calcula litros necesarios, arma la combinación de envases, y suma
precios — todo con código Python determinístico. El LLM (real o mock) solo recibe esos
números ya calculados y los redacta en un texto amigable. Un modelo de lenguaje puede
"alucinar" un número creíble pero incorrecto; el código no.

**Bug real que encontramos armando esto**: el primer algoritmo de combinación de envases
elegía por tamaño (más grande primero) sin comparar el costo total, y en un caso terminó
recomendando comprar un bidón de 20L ($98.000) cuando 8 baldes de 1L ($52.000) cubrían
exactamente lo mismo. Lo corregimos a una búsqueda que compara el costo real de cada
combinación posible antes de elegir. Quedó como test automático
(`test_combinacion_de_envases_elige_la_mas_barata_no_la_mas_grande`) para que nunca vuelva a
pasar sin que alguien se entere.

## Por qué "pedir aclaración" en vez de "no sé" o "derivar"

El asistente de MIFE es interno — lo usa un vendedor que está en medio de la conversación con
el cliente. Si falta un dato (metros cuadrados, color), lo correcto es que el asistente se lo
pida AL VENDEDOR (para que se lo pregunte al cliente), no que responda genéricamente "no sé" o
que lo mande a otra persona — el vendedor mismo puede resolver el faltante con una pregunta.

## Sobre el audio

Convertir audio a texto (transcripción) requiere un servicio externo real (Whisper API,
Google Speech-to-Text, etc.) que no se puede usar en este entorno de desarrollo sin salida a
internet general. `adaptadores_mcp/transcripcion.py` deja el mismo patrón mock/real que el
resto del proyecto: en mock, el "audio" ya llega como texto (para poder probar todo el resto
del sistema); en real, queda documentado qué hace falta conectar cuando MIFE elija un
servicio.

## MCP

`adaptadores_mcp/stock_server.py` usa el SDK oficial de MCP (protocolo real, no
reimplementado), con guardrail de formato de SKU (rechaza cualquier cosa que no tenga el
formato `MIFE-...` antes de tocar el catálogo — probado con un intento de inyección en los
tests).

## Pendiente para producción real

- Reemplazar los embeddings TF-IDF locales por un modelo real si el catálogo crece mucho.
- Conectar un servicio real de transcripción de audio.
- Sumar autenticación al servicio HTTP antes de exponerlo fuera de la red interna de MIFE.
