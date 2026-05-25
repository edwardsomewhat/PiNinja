"""Abstract runner interface for sub-agent backends."""
from abc import ABC, abstractmethod
from ..packet import ResultPacket
from ..config import SubNinjaConfig


class Runner(ABC):
    """A runner invokes a sub-agent against a specific model backend."""

    @abstractmethod
    def run(
        self,
        config: SubNinjaConfig,
        mission_context: str,
    ) -> ResultPacket:
        """Execute the sub-agent and return a structured result packet."""
        ...


def get_runner(model_uri: str) -> Runner:
    """Factory: return the appropriate runner for a model URI.

    Supported schemes:
      ollama://host:port/model   → OllamaRunner
      agy://host                 → AgyRunner
      openrouter://provider/model → OpenRouterRunner
    """
    if model_uri.startswith("ollama://"):
        from .ollama import OllamaRunner
        return OllamaRunner()
    elif model_uri.startswith("agy://"):
        from .agy import AgyRunner
        return AgyRunner()
    elif model_uri.startswith("openrouter://"):
        from .openrouter import OpenRouterRunner
        return OpenRouterRunner()
    else:
        raise ValueError(f"Unknown model scheme: {model_uri}")
