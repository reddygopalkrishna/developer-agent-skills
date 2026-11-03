#!/usr/bin/env python3
"""Validate every skill in skills/ against the rules in CONTRIBUTING.md.

Usage:
    python scripts/validate_skills.py              # full check
    python scripts/validate_skills.py --skills-only  # skip marketplace/README checks

Standard library only, so it runs anywhere Python 3.8+ is installed.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
README = ROOT / "README.md"

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ALLOWED_FIELDS = {"name", "description", "license"}
REQUIRED_FIELDS = {"name", "description", "license"}
MAX_NAME = 64
MAX_DESCRIPTION = 1024
MAX_SKILL_LINES = 450
MAX_REFERENCE_LINES = 400
LINK_RE = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")
FENCE_RE = re.compile(r"^(```|~~~).*?^\1", re.MULTILINE | re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")


def strip_code(text):
    """Remove fenced blocks and inline code so example links are not checked."""
    return INLINE_CODE_RE.sub("", FENCE_RE.sub("", text))


def parse_frontmatter(text):
    """Return (fields, body, error). Fields are single-line `key: value` pairs."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, None, "file must start with '---' frontmatter"
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return None, None, "frontmatter is not closed with '---'"
    fields = {}
    for raw in lines[1:end]:
        if not raw.strip():
            continue
        if raw[0].isspace() or ":" not in raw:
            return None, None, f"frontmatter line is not a single-line 'key: value': {raw!r}"
        key, value = raw.split(":", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        elif ": " in value or " #" in value:
            return None, None, f"unquoted ': ' or ' #' in '{key.strip()}' is invalid YAML; quote the value"
        fields[key.strip()] = value
    body = "\n".join(lines[end + 1:])
    return fields, body, None


def check_skill(skill_dir):
    errors = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return [f"{skill_dir.name}: missing SKILL.md"]

    text = skill_md.read_text(encoding="utf-8")
    fields, body, err = parse_frontmatter(text)
    if err:
        return [f"{skill_dir.name}: {err}"]

    missing = REQUIRED_FIELDS - fields.keys()
    extra = fields.keys() - ALLOWED_FIELDS
    if missing:
        errors.append(f"missing frontmatter fields: {sorted(missing)}")
    if extra:
        errors.append(f"non-portable frontmatter fields: {sorted(extra)}")

    name = fields.get("name", "")
    if name != skill_dir.name:
        errors.append(f"name {name!r} does not match folder {skill_dir.name!r}")
    if not NAME_RE.match(name) or len(name) > MAX_NAME:
        errors.append(f"invalid name {name!r} (lowercase, digits, single hyphens, <= {MAX_NAME})")

    desc = fields.get("description", "")
    if not desc:
        errors.append("description is empty")
    if len(desc) > MAX_DESCRIPTION:
        errors.append(f"description is {len(desc)} chars (max {MAX_DESCRIPTION})")
    if "<" in desc or ">" in desc:
        errors.append("description must not contain '<' or '>'")
    if "use when" not in desc.lower():
        errors.append("description should say 'Use when ...'")

    n_lines = len(text.splitlines())
    if n_lines > MAX_SKILL_LINES:
        errors.append(f"SKILL.md is {n_lines} lines (max {MAX_SKILL_LINES})")
    if not re.search(r"^# ", body, re.MULTILINE):
        errors.append("body has no '# Title' heading")

    for md in [skill_md, *sorted((skill_dir / "references").glob("*.md"))]:
        md_text = md.read_text(encoding="utf-8")
        if md != skill_md and len(md_text.splitlines()) > MAX_REFERENCE_LINES:
            errors.append(f"{md.relative_to(skill_dir)} is over {MAX_REFERENCE_LINES} lines")
        for target in LINK_RE.findall(strip_code(md_text)):
            if "://" in target or target.startswith("mailto:"):
                continue
            if not (md.parent / target).resolve().exists():
                errors.append(f"broken link in {md.relative_to(skill_dir)}: {target}")

    refs_dir = skill_dir / "references"
    if refs_dir.is_dir():
        for ref in sorted(refs_dir.glob("*.md")):
            if f"references/{ref.name}" not in text:
                errors.append(f"references/{ref.name} is not linked from SKILL.md")

    for path in skill_dir.rglob("*"):
        if path.is_file() and path.suffix not in {".md"}:
            errors.append(f"non-Markdown file {path.relative_to(skill_dir)} (see CONTRIBUTING.md)")

    return [f"{skill_dir.name}: {e}" for e in dict.fromkeys(errors)]


def check_index(skill_names):
    errors = []
    if not MARKETPLACE.is_file():
        return [f"missing {MARKETPLACE.relative_to(ROOT)}"]
    data = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    listed = []
    for plugin in data.get("plugins", []):
        for path in plugin.get("skills", []):
            target = (ROOT / path).resolve()
            if not (target / "SKILL.md").is_file():
                errors.append(f"marketplace plugin {plugin.get('name')!r} lists missing skill {path}")
            listed.append(target.name)
    for name in skill_names:
        count = listed.count(name)
        if count == 0:
            errors.append(f"{name}: not listed in marketplace.json")
        elif count > 1:
            errors.append(f"{name}: listed in {count} marketplace plugins (must be exactly one)")

    readme = README.read_text(encoding="utf-8") if README.is_file() else ""
    for name in skill_names:
        if f"skills/{name}" not in readme:
            errors.append(f"{name}: not linked from README.md")
    return errors


def main():
    skills_only = "--skills-only" in sys.argv[1:]
    skill_dirs = sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir()) if SKILLS_DIR.is_dir() else []
    if not skill_dirs:
        print("No skills found in skills/")
        return 1

    errors = []
    for skill_dir in skill_dirs:
        errors.extend(check_skill(skill_dir))
    if not skills_only:
        errors.extend(check_index([p.name for p in skill_dirs]))

    if errors:
        print(f"{len(errors)} problem(s) found:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"OK: {len(skill_dirs)} skills valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
