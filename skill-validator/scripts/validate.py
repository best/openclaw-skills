#!/usr/bin/env python3
"""Skill Validator — structural, path-safety, cross-platform, and reference checks."""

import argparse
import json
import os
import py_compile
import re
import stat
import sys
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Issue:
    category: str
    level: str  # "fail" | "warn" | "info"
    message: str
    file: Optional[str] = None


@dataclass
class CategoryResult:
    name: str
    status: str = "pass"
    issues: list = field(default_factory=list)

    def add(self, level: str, msg: str, file: str = None):
        self.issues.append(Issue(self.name, level, msg, file))
        if level == "fail":
            self.status = "fail"
        elif level == "warn" and self.status != "fail":
            self.status = "warn"


@dataclass
class Report:
    skill_name: str = ""
    skill_version: str = ""
    categories: list = field(default_factory=list)
    verdict: str = "pass"

    def add_category(self, cat: CategoryResult):
        self.categories.append(cat)
        if cat.status == "fail":
            self.verdict = "fail"
        elif cat.status == "warn" and self.verdict != "fail":
            self.verdict = "warn"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SCRIPT_EXTENSIONS = {".py", ".sh", ".bash", ".rb", ".pl", ".js", ".ts", ".ps1"}
ALLOWED_TOPLEVEL = {"SKILL.md", "scripts", "references", "assets"}
EXTRANEOUS_FILES = {"README.md", "README", "CHANGELOG.md", "INSTALLATION_GUIDE.md",
                    "QUICK_REFERENCE.md", "LICENSE", "LICENSE.md", ".gitignore"}


def extract_frontmatter(text: str) -> Optional[dict]:
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        return yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None


def iter_scripts(skill_dir: Path):
    for f in skill_dir.rglob("*"):
        if f.is_file() and f.suffix in SCRIPT_EXTENSIONS:
            yield f


def is_meta_line(line: str) -> bool:
    """Check if a line is a regex pattern definition, comment, or similar meta-code."""
    s = line.strip()
    if s.startswith("#"):
        return True
    # Lines defining regex patterns (r"...", re.search, re.compile, pattern lists)
    if any(kw in s for kw in ["re.search", "re.compile", "re.match", "PATTERN", "_PATTERN"]):
        return True
    # Lines that are tuple/list entries with regex patterns
    if s.startswith("(r'") or s.startswith('(r"') or s.startswith("r'") or s.startswith('r"'):
        return True
    return False


# ---------------------------------------------------------------------------
# Check: Structure
# ---------------------------------------------------------------------------

def check_structure(skill_dir: Path) -> CategoryResult:
    cat = CategoryResult("Structure")

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        cat.add("fail", "SKILL.md not found")
        return cat

    text = skill_md.read_text(encoding="utf-8", errors="replace")
    fm = extract_frontmatter(text)
    if fm is None:
        cat.add("fail", "SKILL.md missing YAML frontmatter (--- delimiters)")
        return cat

    if "name" not in fm:
        cat.add("fail", "Frontmatter missing required field: name")
    if "description" not in fm:
        cat.add("fail", "Frontmatter missing required field: description")
    if "version" not in fm:
        cat.add("warn", "Frontmatter missing recommended field: version")

    for entry in skill_dir.iterdir():
        name = entry.name
        if name.startswith("."):
            continue
        if name not in ALLOWED_TOPLEVEL:
            if name in EXTRANEOUS_FILES:
                cat.add("warn", f"Extraneous file: {name}")
            else:
                cat.add("info", f"Unexpected top-level entry: {name}")

    for subdir in ["scripts", "references", "assets"]:
        d = skill_dir / subdir
        if d.is_dir() and not any(d.iterdir()):
            cat.add("warn", f"Empty directory: {subdir}/")

    return cat


# ---------------------------------------------------------------------------
# Check: Path Safety
# ---------------------------------------------------------------------------

HARDCODED_PATHS = [
    (re.compile(r'/root/'), "Hardcoded /root/ path"),
    (re.compile(r'/home/\w+'), "Hardcoded /home/user path"),
    (re.compile(r'C:\\Users\\'), "Hardcoded C:\\Users\\ path"),
    (re.compile(r'/usr/local/(?!bin/env)'), "Hardcoded /usr/local/ path"),
]


def check_path_safety(skill_dir: Path) -> CategoryResult:
    cat = CategoryResult("Path Safety")

    for script in iter_scripts(skill_dir):
        rel = script.relative_to(skill_dir)
        try:
            content = script.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        for pattern, desc in HARDCODED_PATHS:
            found = False
            for line in content.splitlines():
                if is_meta_line(line):
                    continue
                if pattern.search(line):
                    found = True
                    break
            if found:
                cat.add("warn", desc, file=str(rel))

    return cat


# ---------------------------------------------------------------------------
# Check: Script Quality
# ---------------------------------------------------------------------------

def check_script_quality(skill_dir: Path) -> CategoryResult:
    cat = CategoryResult("Script Quality")

    for script in iter_scripts(skill_dir):
        rel = script.relative_to(skill_dir)

        try:
            first_line = script.open("r", encoding="utf-8", errors="replace").readline()
        except Exception:
            continue

        if script.suffix in (".py", ".sh", ".bash", ".rb", ".pl"):
            if not first_line.startswith("#!"):
                cat.add("warn", "Missing shebang line", file=str(rel))

        if script.suffix in (".sh", ".bash"):
            mode = script.stat().st_mode
            if not (mode & stat.S_IXUSR):
                cat.add("warn", "Missing +x permission", file=str(rel))

        if script.suffix == ".py":
            try:
                py_compile.compile(str(script), doraise=True)
            except py_compile.PyCompileError as e:
                cat.add("fail", f"Python syntax error: {e}", file=str(rel))

    return cat


# ---------------------------------------------------------------------------
# Check: Cross-Platform
# ---------------------------------------------------------------------------

BASH_SPECIFIC = [
    (re.compile(r'\[\['), "Bash-specific [[ ]] test"),
    (re.compile(r'declare\s+-[aAilrx]'), "Bash-specific declare"),
    (re.compile(r'\$\{!\w+'), "Bash-specific indirect expansion"),
    (re.compile(r'<<<'), "Bash-specific here-string"),
    (re.compile(r'mapfile|readarray'), "Bash-specific mapfile/readarray"),
]

PATH_CONCAT_RE = re.compile(r"""\+\s*['"][/\\]['"]\s*\+""")


def check_cross_platform(skill_dir: Path) -> CategoryResult:
    cat = CategoryResult("Cross-Platform")

    for script in iter_scripts(skill_dir):
        rel = script.relative_to(skill_dir)
        try:
            content = script.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        if script.suffix in (".sh", ".bash"):
            first_line = content.split("\n", 1)[0]
            if "/bin/sh" in first_line:
                for pattern, desc in BASH_SPECIFIC:
                    for line in content.splitlines():
                        if is_meta_line(line):
                            continue
                        if pattern.search(line):
                            cat.add("warn", f"{desc} in /bin/sh script", file=str(rel))
                            break

        if script.suffix == ".py":
            for line in content.splitlines():
                if is_meta_line(line):
                    continue
                if PATH_CONCAT_RE.search(line):
                    cat.add("warn", "String path concatenation; prefer os.path.join()", file=str(rel))
                    break

    return cat


# ---------------------------------------------------------------------------
# Check: Reference Integrity
# ---------------------------------------------------------------------------

def check_reference_integrity(skill_dir: Path) -> CategoryResult:
    cat = CategoryResult("Reference Integrity")

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return cat

    text = skill_md.read_text(encoding="utf-8", errors="replace")
    link_re = re.compile(r'\[(?:[^\]]*)\]\((?!https?://|#)([^)]+)\)')

    for m in link_re.finditer(text):
        ref = m.group(1).split("#")[0]
        if not ref:
            continue
        if not (skill_dir / ref).exists():
            cat.add("fail", f'References "{ref}" but file not found')

    return cat


# ---------------------------------------------------------------------------
# Check: Size & Tokens
# ---------------------------------------------------------------------------

def check_size(skill_dir: Path) -> CategoryResult:
    cat = CategoryResult("Size & Tokens")

    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        lines = skill_md.read_text(encoding="utf-8", errors="replace").splitlines()
        body_start = 0
        if lines and lines[0].strip() == "---":
            for i, line in enumerate(lines[1:], 1):
                if line.strip() == "---":
                    body_start = i + 1
                    break
        body_lines = len(lines) - body_start
        if body_lines > 500:
            cat.add("warn", f"SKILL.md body is {body_lines} lines (recommended < 500)")

    total = sum(f.stat().st_size for f in skill_dir.rglob("*") if f.is_file())
    if total > 1_000_000:
        cat.add("warn", f"Total size: {total // 1024} KB (recommended < 1MB)")

    refs_dir = skill_dir / "references"
    if refs_dir.is_dir():
        for f in refs_dir.rglob("*.md"):
            try:
                flines = f.read_text(encoding="utf-8", errors="replace").splitlines()
                if len(flines) > 100:
                    head = "\n".join(flines[:20])
                    if "## " not in head and "- [" not in head:
                        cat.add("warn", f"Large file ({len(flines)} lines) without TOC",
                                file=str(f.relative_to(skill_dir)))
            except Exception:
                pass

    return cat


# ---------------------------------------------------------------------------
# Report Rendering
# ---------------------------------------------------------------------------

STATUS_ICON = {"pass": "✅", "warn": "⚠️ ", "fail": "❌"}
LEVEL_ICON = {"fail": "❌", "warn": "⚠️ ", "info": "ℹ️ "}


def render_text(report: Report) -> str:
    lines = []
    lines.append("╔══════════════════════════════════════════╗")
    lines.append("║   Skill Validator Report                  ║")
    title = f"║   {report.skill_name} v{report.skill_version}"
    lines.append(title.ljust(44) + "║")
    lines.append("╠══════════════════════════════════════════╣")

    for cat in report.categories:
        icon = STATUS_ICON[cat.status]
        extra = f" ({len(cat.issues)})" if cat.issues else ""
        line = f"║ {icon} {cat.name:<20s} {cat.status.upper()}{extra}"
        lines.append(line.ljust(44) + "║")

    n_pass = sum(1 for c in report.categories if c.status == "pass")
    n_warn = sum(1 for c in report.categories if c.status == "warn")
    n_fail = sum(1 for c in report.categories if c.status == "fail")

    lines.append("╠══════════════════════════════════════════╣")
    lines.append(f"║ Verdict: {report.verdict.upper()}".ljust(44) + "║")
    lines.append(f"║ {n_pass} passed · {n_warn} warning · {n_fail} failure".ljust(44) + "║")
    lines.append("╚══════════════════════════════════════════╝")

    all_issues = [i for c in report.categories for i in c.issues]
    if all_issues:
        lines.append("")
        lines.append("Details:")
        for issue in all_issues:
            icon = LEVEL_ICON[issue.level]
            loc = f" ({issue.file})" if issue.file else ""
            lines.append(f"{icon}[{issue.category}]{loc} {issue.message}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def validate(skill_dir: Path) -> Report:
    report = Report()

    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        fm = extract_frontmatter(skill_md.read_text(encoding="utf-8", errors="replace"))
        if fm:
            report.skill_name = fm.get("name", skill_dir.name)
            report.skill_version = str(fm.get("version", "?"))

    if not report.skill_name:
        report.skill_name = skill_dir.name

    for check_fn in [check_structure, check_path_safety, check_script_quality,
                     check_cross_platform, check_reference_integrity, check_size]:
        report.add_category(check_fn(skill_dir))

    return report


def main():
    parser = argparse.ArgumentParser(description="Validate an OpenClaw skill")
    parser.add_argument("skill_path", help="Path to skill directory")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    args = parser.parse_args()

    skill_dir = Path(args.skill_path).resolve()
    if not skill_dir.is_dir():
        print(f"Error: {args.skill_path} is not a directory", file=sys.stderr)
        sys.exit(2)

    report = validate(skill_dir)
    if args.strict and report.verdict == "warn":
        report.verdict = "fail"

    print(json.dumps(asdict_report(report), indent=2) if args.json else render_text(report))
    sys.exit(0 if report.verdict in ("pass", "warn") else 1)


def asdict_report(r: Report) -> dict:
    return {
        "skill_name": r.skill_name,
        "skill_version": r.skill_version,
        "verdict": r.verdict,
        "categories": [
            {"name": c.name, "status": c.status,
             "issues": [{"level": i.level, "message": i.message, "file": i.file} for i in c.issues]}
            for c in r.categories
        ],
    }


if __name__ == "__main__":
    main()
