## Application Building Context

Read the following modular context files in order before implementing
or making any architectural decision:

1. `context/project-overview.md` — product definition,
   goals, features, and scope
2. `context/architecture.md` — system structure,
   boundaries, storage model, and invariants
3. `context/code-standards.md` — implementation rules
   and conventions
4. `context/ai-workflow-rules.md` — development workflow,
   scoping rules, and delivery approach
5. `context/progress-tracker.md` (and `context/progress/*.md`) —
   current phase, completed work, open questions, and next steps

### Core Spec Rules

- Keep core specs modular; never merge `project-overview.md`,
  `architecture.md`, `code-standards.md`, and `ai-workflow-rules.md`
  into a single file.
- Update `context/project-overview.md`, `context/architecture.md`,
  `context/code-standards.md`, or `context/ai-workflow-rules.md`
  only when implementation changes scope, architecture/boundaries,
  storage model, coding standards, or workflow rules.

## Branch-Aware Progress Tracking

Never edit `context/progress-tracker.md` directly from a feature
or development branch. Always check the active branch first:

```bash
git branch --show-current
```

- **On `main`:** Update `context/progress-tracker.md` (`## Completed`
  and `## Open Questions`) directly after each meaningful
  implementation change.
- **On any other branch (`feat/*`, `fix/*`, `develop/*`, etc.):**
  Do NOT edit `context/progress-tracker.md`. Write or append a
  fragment file directly inside `context/progress/`:
  - Dated task fragment (recommended for multi-task branches):
    `context/progress/<YYYY-MM-DD>-<task-slug>.md`
  - Branch-named fragment:
    `context/progress/<branch-clean-slug>.md` (replace `/` with `-`)

Use this fragment structure (and record any missing requirements or
open questions in the fragment when off `main`):

```markdown
# Progress Note: <Short Task Title>

- **Summary / Root Cause**:
  - Brief description of the problem or goal.
- **Implementation Changes**:
  - `path/to/file.py`: What changed and why.
- **Verification**:
  - Commands run (`uv run pytest`, `uv run ruff check .`, etc.) and observed results.
```

## Consolidating Progress Fragments

Before merging a PR or preparing a release, consolidate all
`context/progress/*.md` fragments into `context/progress-tracker.md`
using `scripts/consolidate_progress.py`:

```bash
# Preview without modifying files
uv run scripts/consolidate_progress.py --dry-run

# Consolidate into context/progress-tracker.md and archive fragments
uv run scripts/consolidate_progress.py
```

Optional flags: `--delete` (remove fragments instead of moving to
`context/progress/archive/`), `--target <path>`.

## Pre-Finish Verification

1. Confirm the active branch with `git branch --show-current`.
2. If on a non-`main` branch, verify `git diff context/progress-tracker.md`
   is empty and your non-empty fragment exists in `context/progress/*.md`.
3. If preparing a PR/release for consolidation, run
   `uv run scripts/consolidate_progress.py --dry-run` first.
