# tests/test_diagnostician.py
from unittest.mock import patch, MagicMock
from spawner.diagnostician import Diagnostician
from spawner.config import SubNinjaConfig
from spawner.packet import ResultPacket, PacketStatus


def test_diagnostician_creates_config_on_the_fly():
    diag = Diagnostician(primary_model="ollama://hq-ai:11434/qwen3.6:9b")

    failed_packet = ResultPacket(
        role="coder",
        status=PacketStatus.ERROR,
        model="gpt-oss:20b",
        output="Attempted to write auth/routes.py but got ImportError",
        errors=["ImportError: No module named 'jwt'"],
        duration_seconds=12.0,
    )

    config = diag.build_config(failed_packet, "Mission: build auth system")
    assert isinstance(config, SubNinjaConfig)
    assert config.role == "diagnostician"
    assert config.model == "ollama://hq-ai:11434/qwen3.6:9b"
    assert "ImportError" in config.prompt
    assert "jwt" in config.prompt
    assert "auth/routes.py" in config.prompt
    assert "read_file" in config.tools
    assert "write_file" not in config.tools


def test_diagnostician_default_model():
    diag = Diagnostician()
    config = diag.build_config(
        ResultPacket(role="qa", status=PacketStatus.ERROR, model="t",
                     output="Test failed", errors=["assertion error"]),
        "Mission: test"
    )
    assert "qwen3.6:9b" in config.model


@patch("spawner.runners.base.get_runner")
def test_diagnostician_runs(mock_get_runner):
    mock_runner = MagicMock()
    mock_runner.run.return_value = ResultPacket(
        role="diagnostician",
        status=PacketStatus.PASS,
        model="qwen3.6:9b",
        output="Missing dependency: pip install pyjwt",
        errors=[],
    )
    mock_get_runner.return_value = mock_runner

    diag = Diagnostician(primary_model="ollama://hq-ai:11434/qwen3.6:9b")
    failed = ResultPacket(
        role="coder", status=PacketStatus.ERROR, model="gpt-oss:20b",
        output="ImportError in auth/routes.py",
        errors=["No module named 'jwt'"],
        duration_seconds=5.0,
    )

    result = diag.diagnose(failed, "Mission: build auth")
    assert result.role == "diagnostician"
    assert "pyjwt" in result.output
