"""
observabilidad/tracing.py
-----------------------------
Arize Phoenix: corre local (sin cuenta) y muestra el paso a paso de cada cotización en
http://localhost:6006. LangSmith: opcional, se activa solo si hay credenciales.
"""
from __future__ import annotations

import os
import warnings

_phoenix_session = None
_instrumented = False


def habilitar_langsmith(project_name: str = "mife-pinturia") -> bool:
    api_key = os.environ.get("LANGCHAIN_API_KEY")
    if not api_key:
        warnings.warn("LANGCHAIN_API_KEY no seteada: LangSmith queda deshabilitado.", stacklevel=2)
        return False
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = project_name
    return True


def habilitar_phoenix(launch_ui: bool = True):
    global _phoenix_session, _instrumented
    import phoenix as px
    from openinference.instrumentation.langchain import LangChainInstrumentor

    if launch_ui and _phoenix_session is None:
        _phoenix_session = px.launch_app()
    if not _instrumented:
        LangChainInstrumentor().instrument()
        _instrumented = True
    return _phoenix_session
