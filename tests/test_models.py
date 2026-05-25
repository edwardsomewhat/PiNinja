# tests/test_models.py
from packager.models import ModelRegistry, EndpointConfig

DEFAULT_REGISTRY = ModelRegistry()


def test_default_registry_has_all_roles():
    roles = DEFAULT_REGISTRY.list_roles()
    assert "scout" in roles
    assert "coder" in roles
    assert "builder" in roles
    assert "reviewer" in roles
    assert "qa" in roles


def test_get_endpoint_returns_primary():
    endpoint = DEFAULT_REGISTRY.get_endpoint("coder")
    assert endpoint.primary == "ollama://hq-ai:11434/gpt-oss:20b"
    assert endpoint.fallback == "openrouter://minimax/minimax-m2.5"


def test_get_endpoint_unknown_role_raises():
    import pytest
    with pytest.raises(KeyError, match="noob"):
        DEFAULT_REGISTRY.get_endpoint("noob")


def test_override_model_updates_primary():
    registry = ModelRegistry()
    registry.override("coder", "ollama://hq-ai:11434/nemotron3:33b")
    endpoint = registry.get_endpoint("coder")
    assert endpoint.primary == "ollama://hq-ai:11434/nemotron3:33b"
    assert endpoint.fallback == "openrouter://minimax/minimax-m2.5"


def test_to_endpoints_yaml():
    yaml_dict = DEFAULT_REGISTRY.to_endpoints_dict()
    assert yaml_dict["coder"]["primary"] == "ollama://hq-ai:11434/gpt-oss:20b"
    assert yaml_dict["coder"]["fallback"] == "openrouter://minimax/minimax-m2.5"
    assert yaml_dict["reviewer"]["primary"] == "openrouter://minimax/minimax-m2.5"
