"""Repository-wide hygiene helpers used by shared/tests.

Second line of defence behind Gitleaks (see .github/workflows/validate.yml).
"""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

SENSITIVE = [
    (r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "IPv4 address"),
    (r"\b[0-9a-fA-F]{32}-[0-9a-fA-F]{2}\b", "Falcon CID format"),
    (r"(?i)\b(bearer|api[_-]?key|client[_-]?secret)\s*[:=]\s*\S+", "credential assignment"),
    (r"AKIA[0-9A-Z]{16}", "AWS access key id"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "private key block"),
    (r"\bgh[pousr]_[A-Za-z0-9]{36,}\b", "GitHub token"),
    (r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}", "JWT"),
]

TEXT_SUFFIXES = {".cql", ".md", ".csv", ".svg", ".yml", ".yaml", ".py", ".json", ".toml", ".txt", ".sh"}
SKIP_PARTS = {".git", "node_modules", "__pycache__", ".pytest_cache"}
LINK = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")


def tracked_paths(root: Path = REPO_ROOT):
    for p in sorted(root.rglob("*")):
        if p.is_file() and not (SKIP_PARTS & set(p.relative_to(root).parts)):
            yield p


def text_files(root: Path = REPO_ROOT):
    for p in tracked_paths(root):
        if p.suffix in TEXT_SUFFIXES or p.name in {".gitignore", ".gitleaks.toml"}:
            yield p


def findings_in_text(text: str):
    return [label for pattern, label in SENSITIVE if re.search(pattern, text)]


def broken_links(md_path: Path):
    bad = []
    for target in LINK.findall(md_path.read_text(encoding="utf-8")):
        if re.match(r"^[a-z]+://", target) or target.startswith("mailto:"):
            continue
        if not (md_path.parent / target).exists():
            bad.append(target)
    return bad
