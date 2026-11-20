# Code Standards

These conventions incorporate the project's installed skills (`modern-python`, `python-design-patterns`, `python-configuration`, `python-resilience`, `python-testing-patterns`, `fastapi`, `docker-compose-patterns`, `docker-patterns`, `prompt-engineering-patterns`, `systemd-services`).

## General

- **KISS & Single Responsibility (SRP):** Keep modules, classes, and functions small (typically 20–50 lines) with shallow nesting and early returns. Each unit must have one reason to change.
- **Composition Over Inheritance:** Build the voice pipeline by composing small adapters (audio input, wake-word detector, VAD recorder, STT/LLM/TTS clients, audio output) behind narrow `Protocol` interfaces rather than deep class hierarchies.
- **Dependency Injection:** Inject `Settings`, audio devices, and HTTP clients into the state machine via constructors so all core logic is unit-testable without Pi hardware or a running AI server.
- **Rule of Three:** Do not introduce speculative abstractions or plugin frameworks before three concrete use cases require them.
- **Fix Root Causes:** Never layer silent `except Exception: pass` workarounds over audio, VAD, or network bugs.

## Python Tooling & Style (`modern-python`)

- **Runtime & Package Manager:** Target Python `>=3.11` (`requires-python = ">=3.11"`). Manage dependencies and dev/lint/test `[dependency-groups]` with `uv` (`uv add`, `uv remove`, `uv sync`, `uv.lock`). Use `uv run <cmd>` rather than manual virtualenv activation during development.
- **Linting & Formatting:** Use `ruff` (`line-length = 100`, `target-version = "py311"`, `select = ["ALL"]` with explicit project ignores in `pyproject.toml`). Run `uv run ruff check .` and `uv run ruff format --check .`.
- **Static Type Checking:** Use `ty` (`[tool.ty.environment] python-version = "py311"`, `[tool.ty.terminal] error-on-warning = true`). Annotate all public functions, method signatures, and boundary data structures; avoid untyped `dict[str, Any]` for domain contracts.
- **Layout:** Use `src/voice_assistant/` package layout and PEP 723 inline metadata for any standalone diagnostic/setup scripts.

## Configuration Management (`python-configuration`)

- **Typed Settings:** Define a central `Settings(BaseSettings)` model using `pydantic-settings` and `pydantic.Field` loading from `.env` (`env_file=".env"`, `env_file_encoding="utf-8"`).
- **Fail Fast at Startup:** Validate all required env vars (`STT_URL`, `LLM_URL`, `TTS_URL`, audio parameters, thresholds) when the application boots. On `ValidationError`, print clear field-level diagnostics to stderr and exit non-zero.
- **No Scattered `os.getenv()`:** Never read `os.environ` or `os.getenv()` inside business or client modules; pass `Settings` via dependency injection.
- **Secrets Hygiene:** Never commit `.env` files or API tokens; commit `.env.example` documenting every variable from the PRD Section 4.1 contract. Never log raw env values that could contain credentials.

## Resilience & Error Handling (`python-resilience`)

- **Explicit Timeouts Everywhere:** Every `httpx` request (STT, LLM, TTS) MUST enforce `HTTP_TIMEOUT_SEC` (default `25` s) via `httpx.Timeout`.
- **Retry Only Transient Failures:** Use `tenacity` (`wait_exponential_jitter` + bounded `stop_after_attempt` / `stop_after_delay`) strictly for transient transport errors (`httpx.ConnectError`, `httpx.ReadTimeout`, `TimeoutError`, `ConnectionError`) and transient HTTP statuses (`429`, `502`, `503`, `504`)—keeping total retry delay tight so it does not violate the voice UX latency budget.
- **Never Retry Permanent Errors:** Do not retry `ValueError`, `TypeError`, or HTTP `4xx` client errors (other than `429`).
- **Log & Recover Gracefully:** Log retry attempts and HTTP/audio errors with structured context; on unrecoverable turn failure, transition cleanly to `ERROR` (play `chime_err.wav`) and return to `IDLE`.

## FastAPI Wrappers (`fastapi`, if custom STT/TTS endpoints are written)

- **Parameters & Dependencies:** Always use `Annotated[...]` for `Path`, `Query`, `Form`, `File`, and `Depends(...)` (define reusable dependency type aliases). Never use `...` (ellipsis) as a default value in path operations or Pydantic models, and never use `RootModel`.
- **Sync vs Async:** Use regular `def` path operations (not `async def`) when calling blocking CPU/GPU inference libraries (`faster-whisper`, `piper`) so FastAPI offloads them to its threadpool without blocking the event loop. Use `async def` only with truly non-blocking async libraries.
- **Response Models & Limits:** Declare explicit return type annotations or `response_model` (do not use deprecated `ORJSONResponse`/`UJSONResponse`), enforce `max_body_size` on audio upload routes, and keep one HTTP operation per function.

## Docker & Compose (`docker-compose-patterns`, `docker-patterns`)

- **Canonical Naming:** Use `compose.yaml` and `compose.override.yaml` (Docker Compose v2); do not use legacy `docker-compose.yml`.
- **Image & Restart Hygiene:** Pin specific image versions/tags (never `:latest`), set `restart: unless-stopped` on server services, and configure `healthcheck`s + `depends_on: condition: service_healthy` where services depend on readiness.
- **Volumes & Security:** Persist downloaded STT/LLM/TTS model caches in named `volumes:`. Keep secrets/env overrides in `.env` (`env_file:`), never hardcoded in `compose.yaml`. Run custom containers as non-root with `no-new-privileges:true` where applicable.
- **Validation:** Run `docker compose config --quiet` (never plain `docker compose config` in logs if secrets may interpolate) after every Compose change.

## Prompt Engineering (`prompt-engineering-patterns`)

- **Prompt as Versioned Config:** Store the LLM spoken-assistant system prompt in a dedicated module/config constant—not buried inline inside network plumbing—and document why constraints exist.
- **Spoken Output Constraints:** System prompt MUST enforce plain spoken prose (no Markdown formatting, no bullet lists, no asterisks, no URLs) and concise 1–3 sentence answers to minimize TTS synthesis latency.

## `systemd` & Linux Service Standards (`systemd-services`)

- **Unit Ordering & Supervision:** `voice-assistant.service` MUST declare `After=network-online.target sound.target` and `Wants=network-online.target`, run as a non-root user (`User=pi` or service user with `audio` access), set `WorkingDirectory`, use `EnvironmentFile=` / `.env`, configure `Restart=always` (or `on-failure`) with `RestartSec=5`, and log to `journal` (`StandardOutput=journal`, `StandardError=journal`).
- **Lifecycle Commands:** Reload units with `sudo systemctl daemon-reload`, inspect health via `systemctl status` and `journalctl -u voice-assistant.service -f`.

## Testing (`python-testing-patterns`)

- **Organization & Naming:** Place tests under `tests/` (`conftest.py`, `tests/unit/`, `tests/integration/`) using Arrange-Act-Assert and descriptive names (`test_<unit>_<scenario>_<expected_outcome>`).
- **Hardware & Network Isolation:** Mock PortAudio (`sounddevice`), `aplay`, `openWakeWord`, and `httpx` (`httpx.MockTransport`) in unit tests so the full suite runs deterministically on any dev machine without Pi hardware.
- **Coverage Target:** Maintain `>=80%` unit test coverage (`uv run pytest --cov=voice_assistant --cov-fail-under=80`), covering state transitions, silence timeout (`E2E-05`), offline recovery (`E2E-06`), rolling history truncation (`E2E-03`), and retry boundaries.
