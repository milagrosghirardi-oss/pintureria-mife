"""
adaptadores_mcp/transcripcion.py
------------------------------------
Adaptador para convertir un audio del cliente en texto ("transcripción"). Como convertir
audio a texto de verdad requiere un servicio externo (ej. Whisper de OpenAI, Google
Speech-to-Text) que no podemos usar en este entorno de desarrollo (necesita descargar un
modelo pesado o pagar una API), este adaptador queda con el mismo patrón mock/real que el
resto del proyecto:

  - "mock" (default): asume que el "audio" ya viene como texto (simula que la transcripción
    ya se hizo) — permite construir y probar TODO el resto del sistema sin esa pieza externa.
  - "real": placeholder documentado, listo para conectar un servicio real cuando MIFE lo
    necesite de verdad (ver TRANSCRIPCION_MODE en .env.example).
"""
from __future__ import annotations

import os


class TranscriptorMock:
    def transcribir(self, audio_o_texto: str) -> str:
        """En modo mock, el 'audio' ya llega como texto (para poder probar el resto del
        pipeline sin necesitar grabaciones reales)."""
        return audio_o_texto


class TranscriptorReal:
    """Placeholder: acá se conectaría un servicio real de speech-to-text (ej. Whisper API,
    Google Speech-to-Text, AssemblyAI). No implementado en este demo — requiere elegir el
    servicio y conseguir credenciales, algo para decidir cuando MIFE esté lista para esa
    etapa."""

    def transcribir(self, ruta_audio: str) -> str:
        raise NotImplementedError(
            "Transcripción real no configurada todavía. Ver adaptadores_mcp/transcripcion.py "
            "para conectar un servicio real (Whisper API, Google Speech-to-Text, etc.)."
        )


def get_transcriptor():
    modo = os.environ.get("TRANSCRIPCION_MODE", "mock")
    return TranscriptorReal() if modo == "real" else TranscriptorMock()
