# tests/test_runners.py
from unittest.mock import patch, MagicMock
from spawner.runners.ollama import OllamaRunner
from spawner.config import SubNinjaConfig
from spawner.packet import ResultPacket, PacketStatus


def make_coder_config():
    return SubNinjaConfig(
        role="coder",
        model="ollama://hq-ai:11434/gpt-oss:20b",
        fallback="openrouter://minimax/minimax-m2.5",
        prompt="You are a Shinobi Coder. Write clean Python.",
        tools=["read_file", "write_file", "terminal"],
        mission_id="test-001",
    )


@patch("spawner.runners.ollama.requests.post")
def test_ollama_runner_sends_correct_payload(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "message": {"role": "assistant", "content": "Generated auth/routes.py"}
    }
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    runner = OllamaRunner()
    config = make_coder_config()
    result = runner.run(config, "Mission: build auth system")

    assert result.role == "coder"
    assert result.status == PacketStatus.PASS
    assert "auth/routes.py" in result.output

    # Verify the POST payload
    call_args = mock_post.call_args
    sent_url = call_args[0][0]
    sent_json = call_args[1]["json"]

    assert "11434" in sent_url
    assert sent_json["model"] == "gpt-oss:20b"
    assert sent_json["stream"] is False
    assert len(sent_json["messages"]) >= 2
    assert sent_json["messages"][0]["role"] == "system"
    assert "Shinobi Coder" in sent_json["messages"][0]["content"]


@patch("spawner.runners.ollama.requests.post")
def test_ollama_runner_parses_model_from_uri(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "message": {"role": "assistant", "content": "Done"}
    }
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    runner = OllamaRunner()
    config = SubNinjaConfig(
        role="scout",
        model="ollama://hq-ai:11434/qwen3.6:9b",
        fallback="openrouter://minimax/minimax-m2.5",
        prompt="Scout agent",
        tools=["read_file", "search_files"],
        mission_id="test-002",
    )
    runner.run(config, "Explore the codebase")

    sent_json = mock_post.call_args[1]["json"]
    assert sent_json["model"] == "qwen3.6:9b"


@patch("spawner.runners.ollama.requests.post")
def test_ollama_runner_handles_error(mock_post):
    mock_post.side_effect = Exception("Connection refused")

    runner = OllamaRunner()
    config = make_coder_config()
    result = runner.run(config, "Mission: test")

    assert result.status == PacketStatus.ERROR
    assert "Connection refused" in result.errors[0]


# --- Agy Runner tests ---

@patch("spawner.runners.agy.subprocess.run")
def test_agy_runner_ssh_command(mock_run):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Built and deployed Docker container"
    mock_result.stderr = ""
    mock_run.return_value = mock_result

    from spawner.runners.agy import AgyRunner
    runner = AgyRunner()
    config = SubNinjaConfig(
        role="builder",
        model="agy://hq-ai",
        fallback="openrouter://minimax/minimax-m2.5",
        prompt="You are a Shinobi Builder.",
        tools=["terminal", "write_file"],
        mission_id="test-003",
    )

    result = runner.run(config, "Mission: deploy auth service")

    assert result.role == "builder"
    assert result.status == PacketStatus.PASS
    assert "Docker" in result.output

    # Verify SSH command was called
    cmd_args = mock_run.call_args[0][0]
    assert "ssh" in cmd_args
    assert "hq-ai" in cmd_args
    assert "agy" in cmd_args


@patch("spawner.runners.agy.subprocess.run")
def test_agy_runner_handles_failure(mock_run):
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "agy: command not found"
    mock_run.return_value = mock_result

    from spawner.runners.agy import AgyRunner
    runner = AgyRunner()
    config = SubNinjaConfig(
        role="builder",
        model="agy://hq-ai",
        fallback="openrouter://minimax/minimax-m2.5",
        prompt="Builder",
        tools=["terminal"],
        mission_id="test-fail",
    )

    result = runner.run(config, "Mission: test")
    assert result.status == PacketStatus.ERROR
    assert "command not found" in result.errors[0]


@patch("spawner.runners.agy.subprocess.run")
def test_agy_runner_handles_timeout(mock_run):
    import subprocess
    mock_run.side_effect = subprocess.TimeoutExpired("ssh", 600)

    from spawner.runners.agy import AgyRunner
    runner = AgyRunner()
    config = SubNinjaConfig(
        role="builder",
        model="agy://hq-ai",
        fallback="openrouter://minimax/minimax-m2.5",
        prompt="Builder",
        tools=["terminal"],
        mission_id="test-timeout",
    )

    result = runner.run(config, "Mission: test")
    assert result.status == PacketStatus.ERROR
    assert "Timeout" in result.errors[0]


# --- OpenRouter Runner tests ---

@patch("spawner.runners.openrouter.requests.post")
def test_openrouter_runner_sends_correct_payload(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"role": "assistant", "content": "Code review: LGTM"}}]
    }
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    from spawner.runners.openrouter import OpenRouterRunner
    runner = OpenRouterRunner()
    config = SubNinjaConfig(
        role="reviewer",
        model="openrouter://minimax/minimax-m2.5",
        fallback="openrouter://minimax/minimax-m2.5",
        prompt="You are a Shinobi Reviewer.",
        tools=["read_file", "search_files"],
        mission_id="test-005",
    )

    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
        result = runner.run(config, "Review the auth module")

    assert result.role == "reviewer"
    assert result.status == PacketStatus.PASS

    sent_json = mock_post.call_args[1]["json"]
    assert sent_json["model"] == "minimax/minimax-m2.5"
    assert mock_post.call_args[1]["headers"]["Authorization"] == "Bearer test-key"


@patch("spawner.runners.openrouter.requests.post")
def test_openrouter_missing_api_key(mock_post):
    from spawner.runners.openrouter import OpenRouterRunner
    runner = OpenRouterRunner()
    config = SubNinjaConfig(
        role="qa",
        model="openrouter://minimax/minimax-m2.5",
        fallback="openrouter://minimax/minimax-m2.5",
        prompt="QA agent",
        tools=["terminal"],
        mission_id="test-006",
    )

    with patch.dict("os.environ", {}, clear=True):
        result = runner.run(config, "Run QA")

    assert result.status == PacketStatus.ERROR
    assert "OPENROUTER_API_KEY" in result.errors[0]
    mock_post.assert_not_called()


# --- Fallback Runner tests ---

@patch("spawner.runners.fallback.get_runner")
def test_fallback_runner_tries_primary_first(mock_get_runner):
    mock_primary = MagicMock()
    mock_primary.run.return_value = ResultPacket(
        role="coder", status=PacketStatus.PASS, model="gpt-oss:20b",
        output="Success", duration_seconds=10.0,
    )
    mock_get_runner.return_value = mock_primary

    from spawner.runners.fallback import FallbackRunner
    config = SubNinjaConfig(
        role="coder",
        model="ollama://hq-ai:11434/gpt-oss:20b",
        fallback="openrouter://minimax/minimax-m2.5",
        prompt="Coder",
        tools=["write_file"],
        mission_id="fb-test",
    )
    runner = FallbackRunner()
    result = runner.run(config, "Mission: test")

    assert result.status == PacketStatus.PASS
    assert result.model == "gpt-oss:20b"
    mock_get_runner.assert_called_once_with("ollama://hq-ai:11434/gpt-oss:20b")


@patch("spawner.runners.fallback.get_runner")
def test_fallback_runner_falls_back_on_error(mock_get_runner):
    mock_primary = MagicMock()
    mock_primary.run.return_value = ResultPacket(
        role="coder", status=PacketStatus.ERROR, model="gpt-oss:20b",
        output="", errors=["Connection refused"],
    )
    mock_fallback = MagicMock()
    mock_fallback.run.return_value = ResultPacket(
        role="coder", status=PacketStatus.PASS, model="minimax-m2.5",
        output="Code generated via fallback", duration_seconds=15.0,
    )
    mock_get_runner.side_effect = [mock_primary, mock_fallback]

    from spawner.runners.fallback import FallbackRunner
    config = SubNinjaConfig(
        role="coder",
        model="ollama://hq-ai:11434/gpt-oss:20b",
        fallback="openrouter://minimax/minimax-m2.5",
        prompt="Coder",
        tools=["write_file"],
        mission_id="fb-test-2",
    )
    runner = FallbackRunner()
    result = runner.run(config, "Mission: test")

    assert result.status == PacketStatus.PASS
    assert result.model == "minimax-m2.5"
    assert mock_get_runner.call_count == 2


@patch("spawner.runners.fallback.get_runner")
def test_fallback_runner_no_fallback_configured(mock_get_runner):
    mock_primary = MagicMock()
    mock_primary.run.return_value = ResultPacket(
        role="coder", status=PacketStatus.ERROR, model="test",
        output="", errors=["fail"],
    )
    mock_get_runner.return_value = mock_primary

    from spawner.runners.fallback import FallbackRunner
    config = SubNinjaConfig(
        role="coder",
        model="test-model",
        fallback="",
        prompt="Test",
        tools=[],
        mission_id="fb-no-fb",
    )
    runner = FallbackRunner()
    result = runner.run(config, "Mission: test")

    assert result.status == PacketStatus.ERROR
    assert "No fallback configured" in result.errors[-1]
