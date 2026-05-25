# 🥷 Shinobi

**Deploy. Execute. Vanish.** Zero-footprint coding agent swarm protocol.

Shinobi is the execution layer for Pi Ninja — the persistent coding orchestrator on SovereignAI. It packages coding tasks into self-contained payloads, deploys specialized sub-agents (ninjas) to target directories, orchestrates their work through a full QC pipeline, collects rich intel, and vanishes without a trace.

## Architecture

```
Spec → Packager → payload/ → Dispatcher (with fallback + retry)
    → 5 sub-agents (Scout → Coder → Builder → Reviewer → QA)
    → MissionResult (with recovery data)
    → Vanish → intel.json + archive + purge
    → Processor → memory entries + graphify commands + session summary
```

## Sub-Agents (Ninjas)

| Ninja | Role | Tools |
|-------|------|-------|
| 🥷 Scout | Codebase exploration | grep, read, graphify |
| 🥷 Coder | Implementation | write, edit, bash |
| 🥷 Builder | Compilation, Docker | bash, docker |
| 🥷 Reviewer | Inline QC per step | read, diff |
| 🥷 QA | Final verification | read, test |

## Quick Start

```bash
# Install
pip install -e .

# Package a coding task
shinobi-pack --task "Build a user auth system" --target /path/to/project

# Run the full lifecycle (pack → deploy → vanish → process)
shinobi run --task "Add JWT middleware" --target /path/to/project
```

## Standalone (USB Mode)

Shinobi supports all-API "USB mode" — zero hardware dependencies. Drop a payload on a USB stick, plug it into any machine with Python and internet, and it works:

```yaml
# In payload config — all OpenRouter, no local models
coder:
  primary: openrouter://minimax/minimax-m2.5
  fallback: openrouter://deepseek/deepseek-chat
```

## Recovery Loop

Shinobi handles failures gracefully:
- Primary model fails → auto-fallback
- Subtask errors → up to 3 retries with Diagnostician analysis
- Still failing → escalates with full recovery data in intel packet

## Tests

```bash
pip install -e ".[dev]"
pytest         # 70 tests, all phases
```
