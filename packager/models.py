"""Model registry for Shinobi — role→endpoint mappings with fallback chains."""
from dataclasses import dataclass, field

FALLBACK_MODEL = "openrouter://minimax/minimax-m2.5"

DEFAULT_ENDPOINTS = {
    "scout": {
        "primary": "ollama://hq-ai:11434/qwen3.6:9b",
        "fallback": FALLBACK_MODEL,
    },
    "coder": {
        "primary": "ollama://hq-ai:11434/gpt-oss:20b",
        "fallback": FALLBACK_MODEL,
    },
    "builder": {
        "primary": "agy://hq-ai",
        "fallback": FALLBACK_MODEL,
    },
    "reviewer": {
        "primary": FALLBACK_MODEL,
        "fallback": FALLBACK_MODEL,
    },
    "qa": {
        "primary": FALLBACK_MODEL,
        "fallback": FALLBACK_MODEL,
    },
}


@dataclass
class EndpointConfig:
    role: str
    primary: str
    fallback: str


class ModelRegistry:
    def __init__(self):
        self._endpoints = {}
        for role, config in DEFAULT_ENDPOINTS.items():
            self._endpoints[role] = EndpointConfig(
                role=role,
                primary=config["primary"],
                fallback=config["fallback"],
            )

    def list_roles(self) -> list:
        return list(self._endpoints.keys())

    def get_endpoint(self, role: str) -> EndpointConfig:
        if role not in self._endpoints:
            raise KeyError(f"Unknown role: {role}")
        return self._endpoints[role]

    def override(self, role: str, primary: str):
        if role not in self._endpoints:
            raise KeyError(f"Unknown role: {role}")
        self._endpoints[role].primary = primary

    def to_endpoints_dict(self) -> dict:
        """Convert to dict for endpoints.yaml output."""
        result = {}
        for role, ep in self._endpoints.items():
            result[role] = {
                "primary": ep.primary,
                "fallback": ep.fallback,
            }
        return result
