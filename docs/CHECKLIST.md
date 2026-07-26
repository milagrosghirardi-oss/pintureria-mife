# Checklist de Evaluación

## Repositorio funcional y modular
- 7 carpetas de componentes, cada una con código real y probado.
- 15 tests automáticos (`pytest tests/ -v`), todos pasando.

## Integración MCP segura y conforme al protocolo
- SDK oficial `mcp`, protocolo real (stdio).
- Guardrail de formato de SKU probado con intento de inyección
  (`test_consultar_stock_rechaza_formato_invalido`).

## Observabilidad correctamente instrumentada
- Arize Phoenix (local, real) vía `observabilidad/tracing.py`.
- Métricas propias: latencia, costo, % aclaraciones, % uso de alternativa, anclaje numérico.

## Scripts de despliegue funcionando en entornos reales
- Dockerfile + docker-compose + manifiestos de Kubernetes, sintaxis validada.
- *Nota: el entorno usado para desarrollar esto no tiene Docker disponible, así que el build
  de la imagen no se pudo ejecutar acá — recomendamos correr `./despliegue/deploy.sh local`
  como primer paso al recibir el repo.*

## Cómo reproducir todo

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python -m retrieval.ingest --docs data/docs_ejemplo
pytest tests/ -v
python main.py
```
