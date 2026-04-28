"""Tool framework for Agent tool use.

Every tool is a self-describing callable with:
- name: snake_case identifier
- description: what it does (used by LLM to decide when to call it)
- parameters: Pydantic model defining the JSON schema of arguments
- execute(): the actual implementation (async)

This maps directly to OpenAI's function-calling / Tools API.
"""

from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ValidationError


class ToolError(Exception):
    """Raised when a tool execution fails."""

    def __init__(self, tool_name: str, message: str) -> None:
        self.tool_name = tool_name
        super().__init__(f"Tool '{tool_name}' failed: {message}")


class Tool(ABC):
    """Base class for all Agent tools.

    Subclass must define:
        name: str
        description: str
        parameters: type[BaseModel]
    """

    name: str = ""
    description: str = ""
    parameters: type[BaseModel] | None = None

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Any:
        """Execute the tool with validated arguments."""
        ...

    def to_openai_schema(self) -> dict[str, Any]:
        """Return OpenAI-compatible tool schema."""
        if self.parameters is None:
            params_schema: dict[str, Any] = {"type": "object", "properties": {}}
        else:
            params_schema = self.parameters.model_json_schema()
            # Remove title clutter, keep it clean for LLM context
            params_schema.pop("title", None)
            for prop in params_schema.get("properties", {}).values():
                prop.pop("title", None)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": params_schema,
            },
        }

    async def run(self, raw_args: dict[str, Any]) -> Any:
        """Validate arguments and execute.

        Args:
            raw_args: JSON-decoded arguments from LLM tool_call.

        Returns:
            Tool execution result (must be JSON-serializable).

        Raises:
            ToolError: On validation or execution failure.
        """
        if self.parameters is not None:
            try:
                validated = self.parameters.model_validate(raw_args)
                kwargs = validated.model_dump()
            except ValidationError as e:
                raise ToolError(self.name, f"Invalid arguments: {e}")
        else:
            kwargs = raw_args

        try:
            result = await self.execute(**kwargs)
            return result
        except ToolError:
            raise
        except Exception as e:
            raise ToolError(self.name, str(e))


class SimpleTool(Tool):
    """Convenience wrapper for function-based tools.

    Usage:
        async def my_tool(query: str, top_k: int = 5) -> list[dict]:
            ...

        tool = SimpleTool(
            name="search_knowledge",
            description="Search medical knowledge base",
            func=my_tool,
        )
    """

    def __init__(
        self,
        name: str,
        description: str,
        func: Any,
        parameters: type[BaseModel] | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self._func = func
        if parameters is None:
            # Auto-generate from function signature if possible
            parameters = _infer_params_from_func(func)
        self.parameters = parameters

    async def execute(self, **kwargs: Any) -> Any:
        if inspect.iscoroutinefunction(self._func):
            return await self._func(**kwargs)
        return self._func(**kwargs)


def _infer_params_from_func(func: Any) -> type[BaseModel] | None:
    """Try to infer a Pydantic model from a function signature.

    Returns None if the function takes no arguments.
    """
    sig = inspect.signature(func)
    fields: dict[str, Any] = {}
    for param_name, param in sig.parameters.items():
        if param_name in ("self", "cls"):
            continue
        annotation = param.annotation if param.annotation != inspect.Parameter.empty else Any
        default = param.default if param.default != inspect.Parameter.empty else ...
        fields[param_name] = (annotation, default)

    if not fields:
        return None

    # Dynamically create a Pydantic model
    model_name = f"{func.__name__}_params".capitalize()
    return type(model_name, (BaseModel,), {"__annotations__": {k: v[0] for k, v in fields.items()}})
