"""
orquestacion/llm_provider.py
------------------------------
El "LLM" es el modelo de IA que redacta texto (como Claude). Acá lo hacemos intercambiable:
- "mock" (por defecto): un simulador local, gratis, para probar todo sin necesitar una cuenta.
- "claude": Claude de verdad, para cuando el proyecto esté listo para producción real.

Cambiar de uno a otro es solo una variable de entorno, no hay que tocar el resto del código.
"""
from __future__ import annotations

import os
import re
import textwrap
from typing import Any, List, Optional

from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.language_models.llms import LLM

DEFAULT_CLAUDE_MODEL = "claude-sonnet-5"


class MifeLLM(LLM):
    provider: str = "mock"
    model: str = DEFAULT_CLAUDE_MODEL
    max_tokens: int = 800

    @property
    def _llm_type(self) -> str:
        return f"mife-llm-{self.provider}"

    def get_num_tokens(self, text: str) -> int:
        # Aproximación simple (evita depender de tokenizers que necesitan descargar modelos)
        return max(1, len(text) // 4)

    def _call(self, prompt: str, stop: Optional[List[str]] = None,
               run_manager: Optional[CallbackManagerForLLMRun] = None, **kwargs: Any) -> str:
        if self.provider == "claude":
            return self._call_claude(prompt)
        return self._call_mock(prompt)

    def _call_claude(self, prompt: str) -> str:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("LLM_PROVIDER=claude pero falta ANTHROPIC_API_KEY en el entorno.")
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=self.model, max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in response.content if b.type == "text")

    def _call_mock(self, prompt: str) -> str:
        """Simulador simple: arma una respuesta usando el CONTEXTO recibido. No es un LLM de
        verdad, pero se comporta parecido (usa el contexto, no inventa) para poder probar
        todo el resto del sistema sin gastar en API."""
        contexto_match = re.search(r"CONTEXTO:\s*(.*?)\n\nPEDIDO:", prompt, re.DOTALL)
        contexto = contexto_match.group(1).strip() if contexto_match else ""
        if not contexto:
            return "No tengo información suficiente para armar la cotización."
        return textwrap.shorten(contexto.replace("\n", " "), width=500, placeholder=" [...]")


def get_llm(provider: Optional[str] = None) -> MifeLLM:
    provider = provider or os.environ.get("LLM_PROVIDER", "mock")
    model = os.environ.get("CLAUDE_MODEL", DEFAULT_CLAUDE_MODEL)
    return MifeLLM(provider=provider, model=model)
