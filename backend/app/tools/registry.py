"""Tool registry for dynamic tool discovery and execution.

Agents register tools here; the LLM receives the schema list,
decides which tools to call, and the registry routes execution.
"""

from __future__ import annotations

from typing import Any

from app.tools.base import Tool, ToolError


class ToolRegistry:
    """Central registry for all Agent tools."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> "ToolRegistry":
        """Register a tool. Returns self for chaining."""
        if not tool.name:
            raise ValueError("Tool must have a name")
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' already registered")
        self._tools[tool.name] = tool
        return self

    def get(self, name: str) -> Tool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_schemas(self) -> list[dict[str, Any]]:
        """Return all tool schemas in OpenAI format."""
        return [t.to_openai_schema() for t in self._tools.values()]

    async def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool by name with raw JSON arguments.

        Returns a dict with either:
            {"success": True, "result": <tool output>}
        or:
            {"success": False, "error": <error message>}
        """
        tool = self.get(name)
        if tool is None:
            return {"success": False, "error": f"Tool '{name}' not found"}

        try:
            result = await tool.run(arguments)
            return {"success": True, "result": result}
        except ToolError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": f"Unexpected error in '{name}': {e}"}

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)


# Global singleton registry — agents import and register here
GLOBAL_REGISTRY = ToolRegistry()


def register_tool(tool: Tool) -> Tool:
    """Decorator / helper to register a tool globally."""
    GLOBAL_REGISTRY.register(tool)
    return tool
