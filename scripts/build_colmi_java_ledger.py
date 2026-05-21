#!/usr/bin/env python3
"""Build a QRing/Colmi decompiled Java accountability ledger.

This script is intentionally mechanical. Its job is not to "understand" the APK;
its job is to make every .java file visible, classified, and chunkable so agents
cannot claim exhaustive review while silently skipping files.
"""

from __future__ import annotations

import csv
import hashlib
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "docs" / "reference" / "colmi_sibling_packet"
CHUNK_DIR = OUTPUT_DIR / "java_chunks"

SOURCE_TREES = {
    "decompiled": Path(r"D:\feedback\qring\decompiled\sources"),
    "decompiled4": Path(r"D:\feedback\qring\decompiled4\sources"),
}

LEDGER_PATH = OUTPUT_DIR / "java_file_ledger.csv"
SUMMARY_PATH = OUTPUT_DIR / "java_accounting_summary.md"
CHUNK_MANIFEST_PATH = OUTPUT_DIR / "java_grunge_chunk_manifest.csv"
FUNCTION_DICTIONARY_PATH = OUTPUT_DIR / "java_function_dictionary.md"


LEDGER_FIELDS = [
    "ledger_id",
    "source_tree",
    "relative_path",
    "absolute_path",
    "package",
    "class_name",
    "file_size",
    "line_count",
    "sha256",
    "top_level_package",
    "coarse_category",
    "status",
    "data_domains",
    "ble_touch",
    "storage_touch",
    "ui_touch",
    "generated_or_binding",
    "third_party_or_library",
    "imports_relevant",
    "methods_count",
    "constants_or_command_ids",
    "term_hits",
    "calls_relevant",
    "called_by_relevant",
    "general_function",
    "evidence_notes",
    "needs_deep_read",
    "deep_read_priority",
    "deep_read_by",
    "review_status",
]

CHUNK_FIELDS = [
    "chunk_id",
    "chunk_type",
    "source_tree",
    "path_prefix_or_filter",
    "ledger_ids",
    "row_count",
    "status",
    "assigned_agent_id",
    "output_file",
    "review_status",
    "notes",
]


THIRD_PARTY_ROOTS = (
    "_COROUTINE/",
    "com/baidu/",
    "com/batoulapps/",
    "com/blankj/",
    "com/bumptech/",
    "com/chad/",
    "com/contrarywind/",
    "com/elvishew/",
    "com/google/",
    "com/gyf/",
    "com/haibin/",
    "com/hjq/",
    "com/hp/",
    "com/king/",
    "com/liulishuo/",
    "com/luck/",
    "com/nineoldandroids/",
    "com/scwang/",
    "com/squareup/",
    "com/stfalcon/",
    "com/tbuonomo/",
    "com/yalantis/",
    "com/zhangke/",
    "io/fotoapparat/",
    "io/reactivex/",
)

# Some RealSil files are library/DFU/audio noise, but one command-constant class
# has already mattered. Keep matching files visible if they contain relevant terms.
TERTIARY_ROOTS = (
    "com/realsil/",
)


TERM_DOMAINS: dict[str, tuple[str, ...]] = {
    "Bluetooth": ("ble_connection",),
    "Gatt": ("ble_connection",),
    "GATT": ("ble_connection",),
    "UUID": ("ble_connection",),
    "Characteristic": ("ble_connection",),
    "writeCharacteristic": ("ble_connection",),
    "notify": ("ble_connection", "uart_small_data"),
    "CommandHandle": ("uart_small_data",),
    "BleOperateManager": ("ble_connection",),
    "LargeDataHandler": ("bigdata",),
    "LargeDataParser": ("bigdata",),
    "BaseReqCmd": ("uart_small_data",),
    "BaseRspCmd": ("uart_small_data",),
    "StartHeartRateReq": ("hr", "spo2", "uart_small_data"),
    "StopHeartRateReq": ("hr", "spo2", "uart_small_data"),
    "RealTimeHeartRate": ("hr", "uart_small_data"),
    "DeviceSupportReq": ("device_support",),
    "DeviceSupportFunctionRsp": ("device_support",),
    "HeartRate": ("hr",),
    "heartRate": ("hr",),
    "heart": ("hr",),
    "hrv": ("hrv_regular",),
    "HRV": ("hrv_regular",),
    "Hrv": ("hrv_regular",),
    "BloodOxygen": ("spo2",),
    "bloodOxygen": ("spo2",),
    "oxygen": ("spo2",),
    "Oxygen": ("spo2",),
    "SpO2": ("spo2",),
    "spo2": ("spo2",),
    "sleep": ("sleep",),
    "Sleep": ("sleep",),
    "temperature": ("temperature",),
    "Temperature": ("temperature",),
    "battery": ("battery",),
    "Battery": ("battery",),
    "sport": ("steps_sport",),
    "Sport": ("steps_sport",),
    "sync": ("sync_scheduler",),
    "Sync": ("sync_scheduler",),
    "Room": ("storage_db",),
    "Dao": ("storage_db",),
    "database": ("storage_db",),
    "SQLite": ("storage_db",),
}

COMMAND_PATTERNS = {
    "0x69": ("hr", "spo2", "uart_small_data"),
    "0x6A": ("hr", "spo2", "uart_small_data"),
    "0x1E": ("hr", "uart_small_data"),
    "0x3C": ("device_support",),
    "0x75": ("hr", "bigdata"),
    "117": ("hr", "bigdata"),
    "0x5F": ("spo2", "bigdata"),
    "95": ("spo2", "bigdata"),
    "0x49": ("spo2", "bigdata"),
    "73": ("spo2", "bigdata"),
    "0x28": ("hr", "bigdata"),
    "40": ("hr", "bigdata"),
    "0x27": ("sleep", "bigdata"),
    "39": ("sleep", "bigdata"),
    "0x3E": ("sleep", "bigdata"),
    "62": ("sleep", "bigdata"),
    "0x77": ("temperature", "bigdata"),
    "119": ("temperature", "bigdata"),
}

RE_IMPORT = re.compile(r"^import\s+([\w.$*]+);", re.MULTILINE)
RE_PACKAGE = re.compile(r"^package\s+([\w.]+);", re.MULTILINE)
RE_CLASS = re.compile(r"\b(?:class|interface|enum)\s+([A-Za-z_$][\w$]*)")
RE_METHOD = re.compile(
    r"(?:public|private|protected|static|final|synchronized|native|abstract|\s)+"
    r"[\w$<>\[\], ?]+\s+([A-Za-z_$][\w$]*)\s*\([^;{}]*\)\s*\{"
)
RE_HEX = re.compile(r"0x[0-9A-Fa-f]+")
RE_DECIMAL_INTEREST = re.compile(r"(?<![\w])(?:30|39|40|44|57|60|62|73|95|105|106|117|119)(?![\w])")


@dataclass
class JavaRow:
    data: dict[str, str]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def normalize_rel(path: Path) -> str:
    return path.as_posix()


def top_package(rel: str) -> str:
    parts = rel.split("/")
    if parts and parts[0] == "com" and len(parts) >= 2:
        return f"com.{parts[1]}"
    if parts and parts[0] == "io" and len(parts) >= 2:
        return f"io.{parts[1]}"
    return parts[0] if parts else ""


def is_under(rel: str, prefixes: tuple[str, ...]) -> bool:
    return any(rel.startswith(prefix) for prefix in prefixes)


def relevant_imports(imports: list[str]) -> list[str]:
    keep = []
    needles = (
        "oudmon.ble",
        "Bluetooth",
        "BluetoothGatt",
        "BluetoothDevice",
        "Room",
        "Dao",
        "LargeData",
        "CommandHandle",
        "DeviceSupport",
        "StartHeartRateReq",
        "StopHeartRateReq",
        "RealTimeHeartRate",
    )
    for imp in imports:
        if any(n in imp for n in needles):
            keep.append(imp)
    return keep[:20]


def scan_terms(text: str) -> tuple[Counter, set[str]]:
    hits: Counter = Counter()
    domains: set[str] = set()
    for term, term_domains in TERM_DOMAINS.items():
        count = text.count(term)
        if count:
            hits[term] = count
            domains.update(term_domains)
    for term, term_domains in COMMAND_PATTERNS.items():
        if term.startswith("0x"):
            count = len(re.findall(re.escape(term), text, flags=re.IGNORECASE))
        else:
            count = len(re.findall(rf"(?<![\w]){re.escape(term)}(?![\w])", text))
        if count:
            hits[term] = count
            domains.update(term_domains)
    return hits, domains


def extract_constants(text: str) -> str:
    vals = set(RE_HEX.findall(text))
    vals.update(RE_DECIMAL_INTEREST.findall(text))
    # Keep output bounded for CSV readability.
    ordered = sorted(vals, key=lambda x: (not x.startswith("0x"), x))
    return "|".join(ordered[:40])


def classify(rel: str, package: str, class_name: str, text: str, domains: set[str], hits: Counter, rel_imports: list[str]) -> tuple[str, str, bool, str, str]:
    """Return category, status, needs_deep_read, priority, evidence note."""
    rel_lower = rel.lower()
    is_binding = "/databinding/" in rel_lower and class_name.endswith("Binding")
    is_generated = is_binding or rel.endswith("/R.java") or rel.endswith("/BuildConfig.java") or "/R$" in rel
    is_third_party = is_under(rel, THIRD_PARTY_ROOTS)
    is_tertiary = is_under(rel, TERTIARY_ROOTS)
    is_oudmon = rel.startswith("com/oudmon/")
    is_qcwireless = rel.startswith("com/qcwireless/")
    is_cxxyuek = rel.startswith("com/cxxyuek/")

    strong_protocol = bool(rel_imports) or is_oudmon or any(
        k in hits
        for k in (
            "CommandHandle",
            "LargeDataHandler",
            "StartHeartRateReq",
            "StopHeartRateReq",
            "RealTimeHeartRate",
            "DeviceSupportReq",
            "DeviceSupportFunctionRsp",
        )
    )
    has_domain = bool(domains - {"ui_display_only", "third_party", "generated_binding"})

    if is_generated and not strong_protocol:
        domains.add("generated_binding")
        if has_domain:
            # Generated UI with labels like blood oxygen: visible but not behavior.
            return "generated_binding", "classified_excluded_generated_binding", False, "", "Generated binding/resource file; term hits are UI identifiers unless later contradicted."
        return "generated_binding", "classified_excluded_generated_binding", False, "", "Generated binding/resource file."

    if is_third_party and not strong_protocol and not has_domain:
        domains.add("third_party")
        return "third_party_library", "classified_excluded_third_party", False, "", "Known third-party/library package with no relevant domain hits."

    if is_third_party and has_domain and not strong_protocol:
        # Some libraries have generic terms like sync; do not deep-read unless stronger evidence.
        domains.add("third_party")
        return "third_party_library", "classified_excluded_third_party", False, "", "Known third-party/library package; only generic/domain-string hits."

    if is_oudmon:
        return "ble_protocol_sdk", "needs_deep_read", True, "high", "Vendor BLE/protocol SDK package."

    if is_qcwireless and has_domain:
        return "app_orchestration_candidate", "needs_deep_read", True, "high", "QRing app package with target data-domain hits."

    if is_qcwireless:
        return "app_qcwireless", "auto_scanned", False, "", "QRing app package; no target hits in auto scan."

    if is_cxxyuek and has_domain:
        return "obfuscated_candidate", "needs_deep_read", True, "medium", "Obfuscated app package with target data-domain hits."

    if is_cxxyuek:
        return "obfuscated_no_direct_hits", "auto_scanned", False, "", "Obfuscated package; no target hits in auto scan."

    if is_tertiary and (has_domain or "Mmi" in class_name):
        return "tertiary_constants_or_sdk", "needs_deep_read", True, "medium", "Tertiary SDK with relevant command/domain hits."

    if is_tertiary:
        return "tertiary_library", "classified_excluded_third_party", False, "", "Tertiary library package with no relevant hits."

    if has_domain or strong_protocol:
        return "domain_candidate", "needs_deep_read", True, "medium", "Relevant domain or protocol hits."

    return "unknown_or_low_signal", "auto_scanned", False, "", "No relevant hits in auto scan."


def build_rows() -> list[JavaRow]:
    rows: list[JavaRow] = []
    next_id = 1
    for tree_name, root in SOURCE_TREES.items():
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.java")):
            rel = normalize_rel(path.relative_to(root))
            raw = path.read_bytes()
            text = raw.decode("utf-8", errors="replace")
            package_match = RE_PACKAGE.search(text)
            class_match = RE_CLASS.search(text)
            package = package_match.group(1) if package_match else ""
            class_name = class_match.group(1) if class_match else path.stem
            imports = RE_IMPORT.findall(text)
            rel_imports = relevant_imports(imports)
            hits, domains = scan_terms(text)
            methods = RE_METHOD.findall(text)
            constants = extract_constants(text)
            category, status, needs, priority, note = classify(rel, package, class_name, text, domains, hits, rel_imports)
            ble_touch = bool({"ble_connection", "uart_small_data", "bigdata"} & domains)
            storage_touch = "storage_db" in domains
            ui_touch = rel.startswith("com/qcwireless/") or "/databinding/" in rel.lower()
            generated = category == "generated_binding"
            third_party = category in {"third_party_library", "tertiary_library"}
            term_hits = "|".join(f"{term}:{count}" for term, count in hits.most_common(40))
            row = {
                "ledger_id": f"J{next_id:05d}",
                "source_tree": tree_name,
                "relative_path": rel,
                "absolute_path": str(path),
                "package": package,
                "class_name": class_name,
                "file_size": str(path.stat().st_size),
                "line_count": str(text.count("\n") + 1),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "top_level_package": top_package(rel),
                "coarse_category": category,
                "status": status,
                "data_domains": "|".join(sorted(domains)) if domains else "unknown",
                "ble_touch": str(ble_touch).lower(),
                "storage_touch": str(storage_touch).lower(),
                "ui_touch": str(ui_touch).lower(),
                "generated_or_binding": str(generated).lower(),
                "third_party_or_library": str(third_party).lower(),
                "imports_relevant": "|".join(rel_imports),
                "methods_count": str(len(methods)),
                "constants_or_command_ids": constants,
                "term_hits": term_hits,
                "calls_relevant": "",
                "called_by_relevant": "",
                "general_function": "",
                "evidence_notes": note,
                "needs_deep_read": str(needs).lower(),
                "deep_read_priority": priority,
                "deep_read_by": "",
                "review_status": "unreviewed",
            }
            rows.append(JavaRow(row))
            next_id += 1
    return rows


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def rows_by_filter(rows: list[JavaRow], predicate) -> list[JavaRow]:
    return [r for r in rows if predicate(r.data)]


def chunks_for(rows: list[JavaRow], chunk_type: str, source_tree: str, filter_label: str, size: int, start_num: int) -> tuple[list[dict[str, str]], int]:
    chunks: list[dict[str, str]] = []
    for i in range(0, len(rows), size):
        chunk_rows = rows[i : i + size]
        chunk_id = f"CH{start_num:04d}"
        chunks.append(
            {
                "chunk_id": chunk_id,
                "chunk_type": chunk_type,
                "source_tree": source_tree,
                "path_prefix_or_filter": filter_label,
                "ledger_ids": "|".join(r.data["ledger_id"] for r in chunk_rows),
                "row_count": str(len(chunk_rows)),
                "status": "pending",
                "assigned_agent_id": "",
                "output_file": f"docs/reference/colmi_sibling_packet/java_chunks/{chunk_id.lower()}_{chunk_type}.md",
                "review_status": "unreviewed",
                "notes": "",
            }
        )
        start_num += 1
    return chunks, start_num


def build_chunks(rows: list[JavaRow]) -> list[dict[str, str]]:
    chunks: list[dict[str, str]] = []
    n = 1
    data = [r for r in rows if r.data["needs_deep_read"] == "true"]

    groups = [
        (
            "sdk_protocol",
            "decompiled4",
            "decompiled4 com/oudmon/ble protocol SDK",
            rows_by_filter(data, lambda d: d["source_tree"] == "decompiled4" and d["relative_path"].startswith("com/oudmon/ble/")),
            35,
        ),
        (
            "app_orchestration_strong_hits",
            "decompiled4",
            "decompiled4 com/qcwireless/smart target-domain hits",
            rows_by_filter(data, lambda d: d["source_tree"] == "decompiled4" and d["relative_path"].startswith("com/qcwireless/smart/")),
            35,
        ),
        (
            "obfuscated_hits",
            "decompiled",
            "decompiled com/cxxyuek/app/utyi target-domain hits",
            rows_by_filter(data, lambda d: d["source_tree"] == "decompiled" and d["relative_path"].startswith("com/cxxyuek/app/utyi/")),
            40,
        ),
        (
            "tertiary_constants",
            "decompiled4",
            "decompiled4 tertiary SDK relevant constants/domain hits",
            rows_by_filter(data, lambda d: d["source_tree"] == "decompiled4" and d["coarse_category"] == "tertiary_constants_or_sdk"),
            40,
        ),
    ]
    seen: set[str] = set()
    for chunk_type, source_tree, label, group_rows, size in groups:
        deduped = [r for r in group_rows if r.data["ledger_id"] not in seen]
        seen.update(r.data["ledger_id"] for r in deduped)
        new_chunks, n = chunks_for(deduped, chunk_type, source_tree, label, size, n)
        chunks.extend(new_chunks)

    remainder = [r for r in data if r.data["ledger_id"] not in seen]
    new_chunks, n = chunks_for(remainder, "misc_deep_read", "mixed", "remaining needs_deep_read rows", 40, n)
    chunks.extend(new_chunks)
    return chunks


def write_summary(rows: list[JavaRow], chunks: list[dict[str, str]]) -> None:
    total = len(rows)
    by_tree = Counter(r.data["source_tree"] for r in rows)
    by_status = Counter(r.data["status"] for r in rows)
    by_category = Counter(r.data["coarse_category"] for r in rows)
    needs = [r for r in rows if r.data["needs_deep_read"] == "true"]
    by_domain: Counter[str] = Counter()
    for r in rows:
        for domain in r.data["data_domains"].split("|"):
            by_domain[domain] += 1
    needs_by_prefix = Counter("/".join(r.data["relative_path"].split("/")[:3]) for r in needs)
    lines: list[str] = []
    lines.append("# QRing Java accounting summary")
    lines.append("")
    lines.append("Generated by `scripts/build_colmi_java_ledger.py`.")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    for tree, root in SOURCE_TREES.items():
        lines.append(f"- `{tree}`: `{root}`")
    lines.append("")
    lines.append("## Counts")
    lines.append("")
    lines.append(f"- Total `.java` rows: **{total}**")
    lines.append(f"- Needs deep read: **{len(needs)}**")
    lines.append(f"- Generated chunk rows: **{sum(int(c['row_count']) for c in chunks)}** across **{len(chunks)}** chunks")
    lines.append("")
    lines.append("### By source tree")
    lines.append("")
    for key, count in by_tree.most_common():
        lines.append(f"- `{key}`: {count}")
    lines.append("")
    lines.append("### By status")
    lines.append("")
    for key, count in by_status.most_common():
        lines.append(f"- `{key}`: {count}")
    lines.append("")
    lines.append("### By coarse category")
    lines.append("")
    for key, count in by_category.most_common():
        lines.append(f"- `{key}`: {count}")
    lines.append("")
    lines.append("### By domain hit")
    lines.append("")
    for key, count in by_domain.most_common():
        lines.append(f"- `{key}`: {count}")
    lines.append("")
    lines.append("## Highest-volume deep-read prefixes")
    lines.append("")
    for key, count in needs_by_prefix.most_common(30):
        lines.append(f"- `{key}`: {count}")
    lines.append("")
    lines.append("## Current truth statement")
    lines.append("")
    lines.append("This ledger accounts for discovery and auto-classification only. It does **not** mean the files are understood. Any row with `needs_deep_read=true` requires a chunked human/sibling read before implementation claims are made from it.")
    lines.append("")
    lines.append("## Next work")
    lines.append("")
    lines.append("Use `java_grunge_chunk_manifest.csv` to assign fixed chunks. No sibling should claim a chunk complete unless every listed `ledger_id` receives a terminal status or a documented unresolved state.")
    lines.append("")
    SUMMARY_PATH.write_text("\n".join(lines), encoding="utf-8")


def ensure_function_dictionary() -> None:
    if FUNCTION_DICTIONARY_PATH.exists():
        return
    FUNCTION_DICTIONARY_PATH.write_text(
        "# QRing Java function dictionary\n\n"
        "This file grows from chunked deep reads of `java_file_ledger.csv`.\n\n"
        "## Entry template\n\n"
        "```text\n"
        "file:\n"
        "class:\n"
        "method_or_field:\n"
        "kind:\n"
        "general_function:\n"
        "variables_fields:\n"
        "constants_command_ids:\n"
        "inputs:\n"
        "outputs:\n"
        "calls:\n"
        "called_by:\n"
        "ble_service_or_characteristic:\n"
        "database_or_model_touched:\n"
        "data_domains:\n"
        "freshness_truth_implications:\n"
        "evidence_notes:\n"
        "unknowns:\n"
        "confidence:\n"
        "```\n\n",
        encoding="utf-8",
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CHUNK_DIR.mkdir(parents=True, exist_ok=True)
    rows = build_rows()
    write_csv(LEDGER_PATH, LEDGER_FIELDS, [r.data for r in rows])
    chunks = build_chunks(rows)
    write_csv(CHUNK_MANIFEST_PATH, CHUNK_FIELDS, chunks)
    write_summary(rows, chunks)
    ensure_function_dictionary()
    print(f"wrote {LEDGER_PATH} ({len(rows)} rows)")
    print(f"wrote {CHUNK_MANIFEST_PATH} ({len(chunks)} chunks)")
    print(f"wrote {SUMMARY_PATH}")
    print(f"ensured {FUNCTION_DICTIONARY_PATH}")


if __name__ == "__main__":
    main()
