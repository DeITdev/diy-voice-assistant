# AI Workflow Rules

## Approach

Build the project incrementally following a **spec-driven, Test-Driven Development (TDD)** workflow aligned with the PRD's four milestones and staged verification gates:
- **Milestone 1:** Hardware Bench Proof (Stage 1 electrical checklist + Pi 4 I2S/ALSA setup + Stage 2 audio loopback tests)
- **Milestone 2:** Local AI Server Ready (`compose.yaml` STT/LLM/TTS deployment + Stage 3 `curl` API verification)
- **Milestone 3:** MVP Edge Client & Daemon (`src/voice_assistant/` + `pytest` suite + `voice-assistant.service` + Stage 4 `E2E-01`..`E2E-08`)
- **Milestone 4:** Mechanical Enclosure & Post-Enclosure Re-Verification (`E2E-02`, `E2E-04`)

Context files in `context/` and [prd_diy_voice_assistant_speaker_integrated_with_gen_ai.md](file:///Users/Danar/Project/Ngoding/diy-voice-assistant/prd_diy_voice_assistant_speaker_integrated_with_gen_ai.md) define the specification. Always implement against them—do not invent unrequested features or alter hardware pinouts/API contracts silently.

## Test-Driven Development (TDD) Discipline (`test-driven-development`)

- **Iron Law:** For all Python application code (state machine, config validation, VAD logic, HTTP clients, history buffer), write a failing `pytest` test first (`RED`), verify it fails for the expected reason, write minimal code to pass (`GREEN`), and clean up (`REFACTOR`).
- **No Code Before Failing Test:** If production Python code is written before its failing test, delete it and start from the test.
- **Full Suite Verification:** A single green test file is insufficient—run the full project test suite (`uv run pytest`) before claiming any unit is complete.
- **Permitted Exceptions:** Hardware/OS config snippets (`/boot/firmware/config.txt`, `/etc/asound.conf`), `systemd` unit files, and `compose.yaml` are validated via syntax/lint checks (`docker compose config --quiet`, `systemd-analyze verify` where available) and PRD Stage 2/3 verification commands.

## Systematic Debugging Discipline (`systematic-debugging`)

- **Root Cause First:** Never propose or apply quick symptom fixes before investigating the failing layer across the multi-component pipeline (`INMP441 -> ALSA softvol -> openWakeWord -> VAD -> LAN HTTP -> STT -> LLM -> TTS -> aplay -> MAX98357A`).
- **Four Phases:** (1) Reproduce and gather evidence at each boundary, (2) compare against working reference configs/tests, (3) test one minimal hypothesis at a time, (4) write a failing regression test (for Python bugs) before fixing.
- **Architecture Escalation:** If 3+ fix attempts fail on the same bug, stop and reassess the component boundary or architecture with the user.
- **Debian / Pi OS Triage (`debian-linux-triage`):** On the Pi 4, inspect `aplay -l`, `arecord -l`, `alsamixer`, `systemctl status voice-assistant.service`, `journalctl -u voice-assistant.service -n 100 --no-pager`, and `vcgencmd measure_temp` before changing system files.

## Scoping Rules

- Work on **one small, verifiable unit** at a time (e.g., `Settings` config module, or `STTClient`, or `compose.yaml` STT service).
- Do not combine unrelated system boundaries in a single implementation step.
- Do not pull V2+ roadmap items (sentence-level TTS streaming, WS2812B LED ring, custom wake-word training, Home Assistant tool calling) into V1 MVP work unless explicitly requested.

## When to Split Work

Split an implementation step if it combines:
- Raspberry Pi edge Python logic and Local AI Server Docker/FastAPI changes
- OS-level Pi configuration (`/boot/firmware/config.txt`, `/etc/asound.conf`, `systemd`) and application Python code
- Multiple independent HTTP service integrations (STT vs LLM vs TTS) before each contract is verified standalone
- Behavior or parameters not clearly specified in the PRD or `context/` files

## Network & Operational Safety (`homelab-network-readiness` & `docker-compose-patterns`)

- **Staged Hardware/OS Gates:** Do not advance from Stage 1 (pre-power electrical check) to Stage 2 (ALSA audio tests), or from Stage 3 (standalone `curl` tests) to Stage 4 (full E2E voice loop), until the current stage passes.
- **Destructive Command Guardrails:** Never run `docker compose down -v`, `docker volume rm`, or destructive host OS commands without stating what data will be deleted and getting explicit user confirmation.
- **LAN-Only Exposure:** Never configure port-forwarding, public tunnels, or `0.0.0.0` public exposure of admin/service ports outside the trusted LAN.

## Handling Missing Requirements

- Do not invent product behavior or hardware wiring changes not defined in the PRD or `context/` files.
- If a requirement is ambiguous (e.g., GPU vs CPU-only server, exact LAN IP, primary language), record it in `context/progress/<fragment>.md` when on a non-`main` branch (or in `context/progress-tracker.md` under **Open Questions** when on `main`) and resolve it with the user before implementing the dependent component.

## Protected Files

Do not modify without explicit instruction:
- `.agents/skills/*` and `skills-lock.json` (managed via `npx skills`)
- `prd_diy_voice_assistant_speaker_integrated_with_gen_ai.md` (master PRD; update only if user explicitly revises requirements)

## Keeping Docs in Sync

Update the relevant `context/*.md` file whenever implementation changes:
- System architecture, module layout, or invariants -> `context/architecture.md`
- Language/tooling conventions or dependencies -> `context/code-standards.md`
- Product scope, goals, or success criteria -> `context/project-overview.md`
- Completed work, active task, open questions, or ADRs -> `context/progress-tracker.md` (when on `main`) or `context/progress/<fragment>.md` (when on any non-`main` branch)

## Before Moving to the Next Unit

1. The current unit works within its defined scope and passes TDD/stage verification.
2. No invariant in `context/architecture.md` was violated.
3. Quality checks pass for any touched files:
   - Python: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run ty check`
   - Compose (when applicable): `docker compose config --quiet`
4. Progress is recorded in `context/progress-tracker.md` (on `main`) or `context/progress/<fragment>.md` (on non-`main` branches), and `context/progress-tracker.md` has no unintended diff when off `main`.
