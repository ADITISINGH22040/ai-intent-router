from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    @abstractmethod
    def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Execute the tool and return a standard tool response dict."""
