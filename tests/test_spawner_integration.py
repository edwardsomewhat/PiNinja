# tests/test_spawner_integration.py
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from spawner.dispatcher import Dispatcher
from spawner.packet import ResultPacket, PacketStatus
from packager.spec import parse_spec
from packager.models import ModelRegistry
from packager.generator import generate_payload


@patch("spawner.dispatcher.FallbackRunner")
def test_full_pipeline_from_spec_to_dispatch(mock_fb_class):
    mock_fb = MagicMock()
    mock_fb.run.side_effect = [
        ResultPacket(role="scout", status=PacketStatus.PASS, model="test", output="Scout done"),
        ResultPacket(role="coder", status=PacketStatus.PASS, model="test", output="Coder done"),
        ResultPacket(role="builder", status=PacketStatus.PASS, model="test", output="Builder done"),
        ResultPacket(role="reviewer", status=PacketStatus.PASS, model="test", output="Review done"),
        ResultPacket(role="qa", status=PacketStatus.PASS, model="test", output="QA done"),
    ]
    mock_fb_class.return_value = mock_fb

    # Step 1: Generate payload with packager
    spec = parse_spec({
        "mission_id": "full-pipe-001",
        "goal": "Build rate limiter",
        "target_dir": "/tmp/shinobi-full",
        "constraints": {"language": "python", "framework": "flask"},
        "skills": ["tdd"],
    })

    registry = ModelRegistry()
    payload_dir = tempfile.mkdtemp()
    try:
        generate_payload(spec, registry, payload_dir)

        # Step 2: Load and dispatch
        dispatcher = Dispatcher(payload_dir)
        result = dispatcher.run()

        assert result.mission_id == "full-pipe-001"
        assert len(result.packets) == 5
        assert result.all_passed()
        assert "PASSED" in result.summary()
    finally:
        shutil.rmtree(payload_dir)
