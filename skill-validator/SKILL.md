---
name: skill-validator
version: 0.1.0
description: >
  Validate OpenClaw skills for quality, structure, and cross-platform compatibility.
  Use when: (1) receiving a skill archive (.zip/.tar.gz) or directory for review,
  (2) checking a skill before release or installation, (3) running acceptance tests
  on new or updated skills. Produces a structured report with pass/fail/warn verdicts.
---

# Skill Validator

Validate skill packages for structure, path safety, cross-platform compatibility, and runability.

## Usage

```bash
python3 scripts/validate.py <skill-path> [--json] [--strict]
```

- `<skill-path>` — path to skill directory (or extracted archive)
- `--json` — output machine-readable JSON report
- `--strict` — treat warnings as failures (exit code 1)

## Checks Performed

### 1. Structure (required)
- SKILL.md exists with valid YAML frontmatter (`name`, `description` required; `version` recommended)
- No extraneous top-level files (README.md, CHANGELOG.md, etc.)
- Resource directories only: `scripts/`, `references/`, `assets/`
- No empty directories

### 2. Path Safety
- No hardcoded absolute paths in scripts (`/root/`, `/home/`, `C:\Users\`, `/usr/local/`)
- Scripts use portable path resolution (`dirname "$0"`, `$PSScriptRoot`, `__file__`, `__dirname`)
- No OS-specific path separators hardcoded in cross-platform code

### 3. Script Quality
- `.sh` files have executable permission (`+x`)
- Scripts have proper shebang lines
- Python scripts pass `py_compile` syntax check
- Dependencies declared if non-stdlib imports used

### 4. Cross-Platform
- Shell scripts flagged if using bash-specific features without platform restriction
- Path joining uses `os.path.join` / `path.join` instead of string concatenation

### 5. Reference Integrity
- All file paths mentioned in SKILL.md actually exist in the skill directory
- No dead links to scripts/, references/, or assets/ files

### 6. Size & Tokens
- SKILL.md body under 500 lines (warn if exceeded)
- Total skill size under 1MB (warn if exceeded)
- Large reference files (>100 lines) should have table of contents

## Report Format

```
╔══════════════════════════════════════╗
║   Skill Validator Report             ║
║   skill-name v0.1.0                  ║
╠══════════════════════════════════════╣
║ ✅ Structure         PASS            ║
║ ✅ Path Safety       PASS            ║
║ ⚠️  Script Quality    WARN (2)       ║
║ ❌ Reference Integrity FAIL (1)      ║
║ ✅ Size & Tokens     PASS            ║
╠══════════════════════════════════════╣
║ Verdict: FAIL                        ║
║ 3 passed · 1 warning · 1 failure    ║
╚══════════════════════════════════════╝
```

## Thread Workflow (Discord 🧪丨技能校验)

1. User uploads a skill archive
2. Create thread: `{skill-name} v{version} 校验`
3. Extract → validate → post report
4. FAIL → list specific fixes needed
5. PASS → confirm ready for installation
