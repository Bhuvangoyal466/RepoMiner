"""Coverage report import utilities.

Supports:
- coverage.py XML (coverage xml -o coverage.xml)
- lcov (lcov.info)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import re
import xml.etree.ElementTree as ET


@dataclass(frozen=True)
class CoverageFile:
    path: str
    lines_covered: int
    lines_total: int

    @property
    def coverage_pct(self) -> float:
        if self.lines_total <= 0:
            return 0.0
        return (self.lines_covered / self.lines_total) * 100.0


def _normalize_path(p: str) -> str:
    p = p.replace("\\\\", "/")
    p = re.sub(r"^\./", "", p)
    return p


def parse_coverage_py_xml(xml_text: str) -> List[CoverageFile]:
    """Parse coverage.py XML output."""
    root = ET.fromstring(xml_text)
    results: List[CoverageFile] = []

    for cls in root.findall(".//class"):
        filename = cls.attrib.get("filename")
        if not filename:
            continue
        filename = _normalize_path(filename)
        hits = 0
        total = 0
        for line in cls.findall(".//lines/line"):
            total += 1
            if int(line.attrib.get("hits", "0") or 0) > 0:
                hits += 1
        results.append(CoverageFile(path=filename, lines_covered=hits, lines_total=total))

    merged: Dict[str, CoverageFile] = {}
    for item in results:
        cur = merged.get(item.path)
        if not cur:
            merged[item.path] = item
        else:
            merged[item.path] = CoverageFile(
                path=item.path,
                lines_covered=cur.lines_covered + item.lines_covered,
                lines_total=cur.lines_total + item.lines_total,
            )

    return list(merged.values())


def parse_lcov(lcov_text: str) -> List[CoverageFile]:
    """Parse lcov.info format."""
    current: Optional[str] = None
    lines_total = 0
    lines_covered = 0

    results: List[CoverageFile] = []
    for raw in lcov_text.splitlines():
        line = raw.strip()
        if line.startswith("SF:"):
            if current:
                results.append(CoverageFile(path=_normalize_path(current), lines_covered=lines_covered, lines_total=lines_total))
            current = line[3:]
            lines_total = 0
            lines_covered = 0
        elif line.startswith("DA:"):
            try:
                _, rest = line.split("DA:", 1)
                _, count = rest.split(",", 1)
                lines_total += 1
                if int(count) > 0:
                    lines_covered += 1
            except Exception:
                continue
        elif line == "end_of_record":
            if current:
                results.append(CoverageFile(path=_normalize_path(current), lines_covered=lines_covered, lines_total=lines_total))
            current = None
            lines_total = 0
            lines_covered = 0

    if current:
        results.append(CoverageFile(path=_normalize_path(current), lines_covered=lines_covered, lines_total=lines_total))

    merged: Dict[str, CoverageFile] = {}
    for item in results:
        cur = merged.get(item.path)
        if not cur:
            merged[item.path] = item
        else:
            merged[item.path] = CoverageFile(
                path=item.path,
                lines_covered=cur.lines_covered + item.lines_covered,
                lines_total=cur.lines_total + item.lines_total,
            )

    return list(merged.values())


def map_coverage_to_repo(repo_root: Path, items: List[CoverageFile]) -> List[CoverageFile]:
    """Try to map coverage file paths to actual repo-relative paths."""

    repo_files = [p for p in repo_root.rglob("*") if p.is_file()]
    suffix_map: Dict[str, str] = {}
    for p in repo_files:
        rel = _normalize_path(str(p.relative_to(repo_root)))
        suffix_map.setdefault(rel, rel)

    tail_index: Dict[str, str] = {}
    for rel in suffix_map.keys():
        parts = rel.split("/")
        for n in (1, 2, 3, 4):
            if len(parts) >= n:
                tail = "/".join(parts[-n:])
                tail_index.setdefault(tail, rel)

    mapped: List[CoverageFile] = []
    for item in items:
        raw = _normalize_path(item.path)
        candidate = raw
        if (repo_root / candidate).is_file():
            mapped.append(CoverageFile(path=candidate, lines_covered=item.lines_covered, lines_total=item.lines_total))
            continue

        parts = [p for p in raw.split("/") if p]
        found = None
        for n in (4, 3, 2, 1):
            if len(parts) >= n:
                tail = "/".join(parts[-n:])
                if tail in tail_index:
                    found = tail_index[tail]
                    break
        if found:
            mapped.append(CoverageFile(path=found, lines_covered=item.lines_covered, lines_total=item.lines_total))

    return mapped


def load_coverage_from_repo(repo_root: Path) -> List[CoverageFile]:
    """Load coverage reports from common filenames inside a repository clone."""

    candidates = [
        repo_root / "coverage.xml",
        repo_root / ".coverage.xml",
        repo_root / "lcov.info",
        repo_root / "coverage" / "lcov.info",
        repo_root / "coverage" / "coverage.xml",
    ]

    items: List[CoverageFile] = []
    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            raw = candidate.read_text(encoding="utf-8", errors="ignore")
            if candidate.suffix.lower() == ".xml":
                parsed = parse_coverage_py_xml(raw)
            else:
                parsed = parse_lcov(raw)
            items.extend(map_coverage_to_repo(repo_root, parsed))
        except Exception:
            continue

    merged: Dict[str, CoverageFile] = {}
    for item in items:
        cur = merged.get(item.path)
        if not cur:
            merged[item.path] = item
        else:
            merged[item.path] = CoverageFile(
                path=item.path,
                lines_covered=cur.lines_covered + item.lines_covered,
                lines_total=cur.lines_total + item.lines_total,
            )

    return list(merged.values())


def coverage_summary(items: List[CoverageFile]) -> Dict[str, float | int]:
    """Compute a compact coverage summary for reports and dashboards."""

    total_files = len(items)
    total_lines = sum(item.lines_total for item in items)
    covered_lines = sum(item.lines_covered for item in items)
    coverage_pct = (covered_lines / total_lines * 100.0) if total_lines else 0.0
    covered_files = sum(1 for item in items if item.lines_covered > 0)
    return {
        "files": total_files,
        "covered_files": covered_files,
        "lines_covered": covered_lines,
        "lines_total": total_lines,
        "coverage_pct": round(coverage_pct, 2),
    }
