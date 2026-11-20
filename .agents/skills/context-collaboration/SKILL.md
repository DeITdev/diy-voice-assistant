---
name: context-collaboration
description: >-
  Explains and enforces how this repository manages living documentation in context/
  to avoid Git merge conflicts during multi-branch collaboration. Use when onboarding
  to the project's context workflow, documenting completed work, checking branch-aware
  progress tracking rules, or consolidating context/progress/ fragments before a PR or release.
---

# Collaborative Context & Branch-Aware Progress Workflow

This repository uses a modular `context/` specification system paired with branch-isolated progress fragments so multiple contributors and AI agents can work concurrently on separate branches without causing Git merge conflicts in `context/progress-tracker.md`.

## 1. Modular Context Architecture

Read the project context files in order before implementing or making architectural decisions (see [AGENTS.md](../../../AGENTS.md)):

1. `context/project-overview.md` — product definition, goals, features, and scope
2. `context/architecture.md` — system structure, boundaries, storage model, and invariants
3. `context/ui-context.md` — theme, colors, typography, and component conventions
4. `context/code-standards.md` — implementation rules and conventions
5. `context/ai-workflow-rules.md` — development workflow, scoping rules, and delivery approach
6. `context/progress-tracker.md` (and `context/progress/*.md`) — current phase, completed work, open questions, and next steps

### Core Collaboration Rules for Specs

- **Keep core specs modular:** Never merge `project-overview.md`, `architecture.md`, `ui-context.md`, `code-standards.md`, and `ai-workflow-rules.md` into a single file. Keeping them separate reduces token overhead and scopes edits cleanly.
- **Sync specs only when contracts change:** Update `context/architecture.md`, `context/code-standards.md`, `context/ui-context.md`, or `context/project-overview.md` only when implementation changes architecture/boundaries, storage decisions, coding standards, UI conventions, or feature scope.

## 2. Branch-Aware Progress Tracking (Conflict Prevention)

Never edit `context/progress-tracker.md` from a feature or development branch. Multiple branches appending to `## Completed` in the same file is the primary source of merge conflicts.

### Step 1: Check the Active Branch

```bash
git branch --show-current
```

### Step 2: Route Your Progress Note by Branch

| Active Branch | Where to Write | Rule |
| --- | --- | --- |
| `main` | `context/progress-tracker.md` | Update `## Completed` directly. |
| Any other branch (`develop/web`, `feat/*`, `fix/*`, etc.) | `context/progress/<fragment>.md` | **Do NOT edit `context/progress-tracker.md` directly.** |

### Step 3: Name & Format the Fragment File

When on a non-`main` branch, create or append to a Markdown file directly inside `context/progress/`:

- **Dated task fragment (recommended for multi-task branches):**
  `context/progress/<YYYY-MM-DD>-<task-slug>.md`
  Example: `context/progress/2026-11-16-fix-mavatar-blob-upload.md`
- **Branch-named fragment:**
  `context/progress/<branch-clean-slug>.md` (replace `/` with `-`)
  Example: `context/progress/feat-3D-develop.md` or `context/progress/develop-Halim.md`

**Recommended fragment structure:**

```markdown
# Progress Note: <Short Task Title>

- **Summary / Root Cause**:
  - Brief description of the problem or goal.
- **Implementation Changes**:
  - `path/to/file.ts`: What changed and why.
- **Verification**:
  - Commands run (`npx tsc --noEmit`, unit tests, `npm run lint`, `npm run build`) and observed results.
```

> **Open Questions:** If a requirement is missing while on a feature/dev branch, document it in your `context/progress/<fragment>.md` note (or update `## Open Questions` in `context/progress-tracker.md` only when on `main`).

## 3. Consolidating Fragments Before PR or Release

When merging branches or preparing a release, compile all `context/progress/*.md` fragments into `context/progress-tracker.md` using the project script ([scripts/consolidate-progress.ts](../../../scripts/consolidate-progress.ts)):

```bash
# 1. Preview without modifying files (recommended check first)
npm run context:consolidate -- --dry-run

# 2. Consolidate fragments into context/progress-tracker.md and archive them
npm run context:consolidate
```

### What `npm run context:consolidate` Does

1. Scans top-level `.md` files in `context/progress/` (ignores dotfiles like `.gitkeep`, empty files, and subdirectories such as `archive/`).
2. Wraps each non-empty fragment with `<!-- From <filename> -->` and prepends all entries directly under the `## Completed` heading in `context/progress-tracker.md`.
3. Moves processed fragment files to `context/progress/archive/<name>-<ISO-timestamp>.md` so they are preserved for audit without cluttering `context/progress/`.

**Optional flags:**
- `--dry-run` — Prints what would be inserted and which files would be processed without editing or moving anything.
- `--delete` — Deletes processed fragment files instead of moving them to `context/progress/archive/`.
- `--target <path>` — Targets an alternate tracker file instead of `context/progress-tracker.md`.

## 4. Verification Checklist

Before finishing work or opening a PR:

1. Confirm the active branch with `git branch --show-current`.
2. Verify `context/progress-tracker.md` has **no** unintended diff if working on a non-`main` branch (`git diff context/progress-tracker.md`).
3. Verify your new or updated fragment exists in `context/progress/*.md` and is non-empty.
4. If preparing a PR/release for consolidation, run `npm run context:consolidate -- --dry-run` and confirm all expected fragments are detected cleanly.
