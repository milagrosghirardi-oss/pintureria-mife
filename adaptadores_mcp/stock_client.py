"""
adaptadores_mcp/stock_client.py
-----------------------------------
Cliente MCP que habla con adaptadores_mcp/stock_server.py por el protocolo real (stdio:
levanta el servidor como subproceso y le habla en su mismo idioma, JSON-RPC).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_server_params = StdioServerParameters(
    command=sys.executable, args=["-m", "adaptadores_mcp.stock_server"], cwd=str(PROJECT_ROOT)
)


async def call_tool(tool_name: str, arguments: dict[str, Any]) -> dict:
    async with stdio_client(_server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            texto = "".join(b.text for b in result.content if hasattr(b, "text"))
            try:
                return json.loads(texto)
            except json.JSONDecodeError:
                return {"raw": texto}
