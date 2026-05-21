#!/usr/bin/env python3
"""Build a reconciliation index from Colmi Java chunk reports.

The first Java ledger answers "what files exist and which ones need deep read?".
Chunk reports answer "what did siblings actually read?". This script creates a
small bridge table so progress is measurable without manually opening every
markdown report.
"""

from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKET_DIR = REPO_ROOT / "docs" / "reference" / "colmi_sibling_packet"
CHUNK_DIR = PACKET_DIR / "java_chunks"
OUT_CSV = PACKET_DIR / "java_deep_read_index.csv"
OUT_SUMMARY = PACKET_DIR / "java_deep_read_index_summary.md"
LEDGER_PATH = PACKET_DIR / "java_file_ledger.csv"

FIELDS = [
    "ledger_id",
    "chunk_report",
    "relative_path",
    "terminal_status",
    "data_domains",
    "general_function",
    "needs_followup",
    "evidence_notes",
]

LEDGER_RE = re.compile(r"^J\d{5}$")


def clean_cell(cell: str) -> str:
    cell = cell.strip()
    cell = cell.replace("`", "")
    cell = re.sub(r"<br\s*/?>", "; ", cell, flags=re.I)
    cell = re.sub(r"\s+", " ", cell)
    return cell


def split_md_row(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    cells = [clean_cell(c) for c in stripped.strip("|").split("|")]
    if not cells:
        return None
    if LEDGER_RE.match(cells[0]):
        return cells
    if len(cells) > 1 and LEDGER_RE.match(cells[1]):
        return cells
    return None


def row_from_cells(chunk_name: str, cells: list[str]) -> dict[str, str]:
    # Most chunk status tables use:
    # ledger_id | relative_path | terminal_status | data_domains | general_function | ... | evidence_notes | needs_followup
    # Some early reports vary slightly. Preserve best-effort values rather than inventing certainty.
    ledger_idx = 0 if LEDGER_RE.match(cells[0]) else 1
    # Standard chunks start at ledger_id. Some custom reports include a leading row number:
    # n | ledger_id | class | relative_path | terminal_status | data_domains | general_function | ...
    if ledger_idx == 0:
        relative_path = cells[1] if len(cells) > 1 else ""
        terminal_status = cells[2] if len(cells) > 2 else ""
        data_domains = cells[3] if len(cells) > 3 else ""
        general_function = cells[4] if len(cells) > 4 else ""
    else:
        if len(cells) <= 8:
            # compact custom table: # | ledger_id | class | lines | domain | signal | status
            relative_path = cells[2] if len(cells) > 2 else ""
            terminal_status = cells[-1] if len(cells) > 1 else ""
            data_domains = cells[4] if len(cells) > 4 else ""
            general_function = cells[2] if len(cells) > 2 else ""
        else:
            # expanded custom table: # | ledger_id | class | relative_path | terminal_status | data_domains | general_function | ...
            relative_path = cells[3] if len(cells) > 3 else ""
            terminal_status = cells[4] if len(cells) > 4 else ""
            data_domains = cells[5] if len(cells) > 5 else ""
            general_function = cells[6] if len(cells) > 6 else ""
    return {
        "ledger_id": cells[ledger_idx],
        "chunk_report": f"java_chunks/{chunk_name}",
        "relative_path": relative_path,
        "terminal_status": terminal_status,
        "data_domains": data_domains,
        "general_function": general_function,
        "needs_followup": cells[-1] if len(cells) > 1 else "",
        "evidence_notes": cells[-2] if len(cells) > 2 else "",
    }


def main() -> None:
    rows: dict[str, dict[str, str]] = {}
    duplicates: list[tuple[str, str, str]] = []

    for path in sorted(CHUNK_DIR.glob("*.md")):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            cells = split_md_row(line)
            if not cells:
                continue
            row = row_from_cells(path.name, cells)
            old = rows.get(row["ledger_id"])
            if old:
                duplicates.append((row["ledger_id"], old["chunk_report"], row["chunk_report"]))
            rows[row["ledger_id"]] = row

    ordered = [rows[k] for k in sorted(rows)]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(ordered)

    by_chunk = Counter(r["chunk_report"] for r in ordered)
    by_status = Counter(r["terminal_status"] for r in ordered)
    ledger_rows = []
    if LEDGER_PATH.exists():
        with LEDGER_PATH.open(encoding="utf-8", newline="") as f:
            ledger_rows = list(csv.DictReader(f))
    indexed_ids = {r["ledger_id"] for r in ordered}
    needs_ids = {
        r["ledger_id"] for r in ledger_rows
        if r.get("needs_deep_read", "").lower() == "true" or r.get("status") == "needs_deep_read"
    }
    indexed_needs = needs_ids & indexed_ids
    remaining_needs = needs_ids - indexed_ids
    remaining_by_category = Counter(
        r.get("coarse_category", "") for r in ledger_rows if r.get("ledger_id") in remaining_needs
    )

    lines = [
        "# Colmi Java deep-read reconciliation index",
        "",
        "Generated by `scripts/build_colmi_deep_read_index.py`.",
        "",
        "This file reconciles sibling chunk reports back to ledger IDs. It is a progress index, not a replacement for the master ledger or atlas.",
        "",
        f"- Unique ledger IDs documented in chunk reports: **{len(ordered)}**",
        f"- Duplicate ledger IDs encountered across reports: **{len(duplicates)}**",
        f"- Initial `needs_deep_read` rows: **{len(needs_ids)}**",
        f"- Indexed rows that came from `needs_deep_read`: **{len(indexed_needs)}**",
        f"- Initial `needs_deep_read` rows not yet indexed: **{len(remaining_needs)}**",
        "",
        "## By chunk report",
        "",
    ]
    for chunk, count in sorted(by_chunk.items()):
        lines.append(f"- `{chunk}`: {count}")
    lines += ["", "## By terminal status", ""]
    for status, count in sorted(by_status.items()):
        label = status or "(blank)"
        lines.append(f"- `{label}`: {count}")
    lines += ["", "## Remaining initial needs_deep_read by category", ""]
    for category, count in remaining_by_category.most_common():
        label = category or "(blank)"
        lines.append(f"- `{label}`: {count}")
    if duplicates:
        lines += ["", "## Duplicate ledger IDs", ""]
        for ledger_id, first, second in duplicates:
            lines.append(f"- `{ledger_id}`: `{first}` and `{second}`")
    lines += [
        "",
        "## Next reconciliation work",
        "",
        "- Join this index against `java_file_ledger.csv` to compute remaining `needs_deep_read` rows.",
        "- Add atlas section links for high-value rows as atlas pages mature.",
        "- Normalize terminal statuses; early sibling reports used slightly different labels.",
    ]
    OUT_SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT_CSV.relative_to(REPO_ROOT)} ({len(ordered)} rows)")
    print(f"wrote {OUT_SUMMARY.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()



