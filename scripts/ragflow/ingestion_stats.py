#!/usr/bin/env python3
"""
ingestion_stats.py

Aggrega i tempi di ingestion dei documenti RAGFlow via REST API LAN.

Usa i secondi in progress_msg (`Task done (Xs)`) come metrica primaria:
process_duration è wall-clock dal primo tentativo e include coda Redis,
retry e pause (es. Ollama irraggiungibile), quindi può essere fuorviante.

Auth: variabile d'ambiente RAGFLOW_API_KEY (stessa chiave del MCP ragflow-local).
URL:  RAGFLOW_BASE_URL (default https://ragflow-internal.pindaroli.org).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from write_ingestion_report import dataset_profile, write_report

DEFAULT_BASE_URL = "https://ragflow-internal.pindaroli.org"
PAGE_SIZE = 100

TASK_DONE_RE = re.compile(r"Task done \(([\d.]+)s\)", re.IGNORECASE)
STAGE_RES = {
    "ocr": re.compile(r"OCR finished \(([\d.]+)s\)", re.IGNORECASE),
    "layout": re.compile(r"Layout analysis \(([\d.]+)s\)", re.IGNORECASE),
    "table": re.compile(r"Table analysis \(([\d.]+)s\)", re.IGNORECASE),
    "embedding": re.compile(r"Embedding chunks \(([\d.]+)s\)", re.IGNORECASE),
    "indexing": re.compile(r"Indexing done \(([\d.]+)s\)", re.IGNORECASE),
}


class RagflowApiError(RuntimeError):
    pass


def sum_matches(pattern: re.Pattern[str], text: str) -> float | None:
    matches = [float(m) for m in pattern.findall(text or "")]
    if not matches:
        return None
    return sum(matches)


def percentile(sorted_vals: list[float], p: float) -> float | None:
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(sorted_vals) - 1)
    if lo == hi:
        return sorted_vals[lo]
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


def summarize(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {
            "count": 0,
            "sum": 0.0,
            "avg": None,
            "p50": None,
            "p95": None,
            "max": None,
        }
    ordered = sorted(values)
    return {
        "count": len(ordered),
        "sum": sum(ordered),
        "avg": statistics.fmean(ordered),
        "p50": percentile(ordered, 0.50),
        "p95": percentile(ordered, 0.95),
        "max": ordered[-1],
    }


def fmt_s(value: float | None) -> str:
    if value is None:
        return "-"
    if value >= 3600:
        return f"{value / 3600:.1f}h"
    if value >= 60:
        return f"{value / 60:.1f}m"
    return f"{value:.2f}s"


def parse_document(dataset_name: str, dataset_id: str, doc: dict[str, Any]) -> dict[str, Any]:
    progress_msg = doc.get("progress_msg") or ""
    wall = doc.get("process_duration")
    try:
        wall_s = float(wall) if wall is not None else None
    except (TypeError, ValueError):
        wall_s = None

    stages = {name: sum_matches(pattern, progress_msg) for name, pattern in STAGE_RES.items()}
    return {
        "dataset": dataset_name,
        "dataset_id": dataset_id,
        "id": doc.get("id"),
        "name": doc.get("name"),
        "run": doc.get("run") or "UNKNOWN",
        "size": doc.get("size") or 0,
        "chunk_count": doc.get("chunk_count") or 0,
        "process_begin_at": doc.get("process_begin_at"),
        "wall_s": wall_s,
        "task_s": sum_matches(TASK_DONE_RE, progress_msg),
        "stages": stages,
    }


def _direct_opener() -> urllib.request.OpenerDirector:
    """LAN interna: ignora HTTP(S)_PROXY (stesso pattern di scripts/utils/common.py)."""
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


class RagflowClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.opener = _direct_opener()
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "User-Agent": "k8s-lab-ragflow-ingestion-stats/1.0",
        }

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        query = urllib.parse.urlencode(params or {})
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{query}"
        req = urllib.request.Request(url, headers=self.headers, method="GET")
        try:
            with self.opener.open(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:300]
            raise RagflowApiError(f"HTTP {exc.code} su {path}: {body}") from exc
        except urllib.error.URLError as exc:
            raise RagflowApiError(f"Connessione fallita verso {self.base_url}: {exc.reason}") from exc

        if not isinstance(payload, dict):
            raise RagflowApiError(f"Risposta non JSON-object da {path}")
        if payload.get("code") not in (0, None):
            raise RagflowApiError(f"API {path} code={payload.get('code')}: {payload.get('message')}")
        return payload

    def paginate(self, path: str, list_key: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        page = 1
        total: int | None = None
        while True:
            payload = self.get(path, {"page": page, "page_size": PAGE_SIZE})
            data = payload.get("data", payload)
            chunk: list[dict[str, Any]]
            if isinstance(data, list):
                chunk = data
                total = payload.get("total", len(data))
            elif isinstance(data, dict):
                chunk = data.get(list_key) or data.get("docs") or []
                total = data.get("total", payload.get("total"))
            else:
                raise RagflowApiError(f"Formato inatteso da {path}")

            if not isinstance(chunk, list) or not chunk:
                break
            items.extend(chunk)
            if total is not None and len(items) >= int(total):
                break
            if len(chunk) < PAGE_SIZE:
                break
            if page > 1000:
                raise RagflowApiError(f"Troppe pagine su {path}")
            page += 1
        return items

    def list_datasets(self) -> list[dict[str, Any]]:
        return self.paginate("/api/v1/datasets", "kbs")

    def list_documents(self, dataset_id: str) -> list[dict[str, Any]]:
        return self.paginate(f"/api/v1/datasets/{dataset_id}/documents", "docs")


def aggregate_docs(parsed: list[dict[str, Any]]) -> dict[str, Any]:
    by_run: dict[str, int] = {}
    for doc in parsed:
        by_run[doc["run"]] = by_run.get(doc["run"], 0) + 1

    done = [d for d in parsed if d["run"] == "DONE"]
    done_with_task = [d for d in done if d["task_s"] is not None and d["task_s"] > 0]
    missing_task = [d for d in done if d["task_s"] is None or d["task_s"] <= 0]

    stage_values: dict[str, list[float]] = {name: [] for name in STAGE_RES}
    for doc in done_with_task:
        for name, value in doc["stages"].items():
            if value is not None and value > 0:
                stage_values[name].append(value)

    return {
        "fetched": len(parsed),
        "by_run": by_run,
        "missing_task_s": len(missing_task),
        "task": summarize([d["task_s"] for d in done_with_task]),
        "wall": summarize([d["wall_s"] for d in done_with_task if d["wall_s"] is not None]),
        "stages": {name: summarize(vals) for name, vals in stage_values.items()},
    }


def print_table(rows: list[dict[str, Any]]) -> None:
    headers = [
        ("dataset", "dataset", str),
        ("docs", "fetched", str),
        ("done", "done", str),
        ("fail", "fail", str),
        ("other", "other", str),
        ("no_task", "missing_task_s", str),
        ("task_sum", "task_sum", fmt_s),
        ("avg", "task_avg", fmt_s),
        ("p50", "task_p50", fmt_s),
        ("p95", "task_p95", fmt_s),
        ("max", "task_max", fmt_s),
        ("wall_p50", "wall_p50", fmt_s),
        ("wall_p95", "wall_p95", fmt_s),
    ]
    str_rows = []
    for row in rows:
        str_rows.append([fmt(row[key]) if fmt is fmt_s else str(row[key]) for _, key, fmt in headers])
    widths = [len(h[0]) for h in headers]
    for row in str_rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def line(cells: list[str]) -> str:
        return "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(cells))

    print(line([h[0] for h in headers]))
    print("  ".join("-" * w for w in widths))
    for row in str_rows:
        print(line(row))


def print_stage_table(rows: list[dict[str, Any]]) -> None:
    headers = ["dataset", "ocr_p50", "layout_p50", "table_p50", "embed_p50", "index_p50"]
    keys = ["dataset", "ocr_p50", "layout_p50", "table_p50", "embed_p50", "index_p50"]
    str_rows = []
    for row in rows:
        str_rows.append(
            [
                str(row["dataset"]),
                *(fmt_s(row[k]) for k in keys[1:]),
            ]
        )
    if all(cell == "-" for row in str_rows for cell in row[1:]):
        return
    widths = [len(h) for h in headers]
    for row in str_rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    print()
    print("Fasi (p50 sui documenti DONE con Task done > 0; assente se DeepDoc non ha emesso la fase)")
    print("  ".join(h.ljust(widths[i]) for i, h in enumerate(headers)))
    print("  ".join("-" * w for w in widths))
    for row in str_rows:
        print("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)))


def print_top(docs: list[dict[str, Any]], limit: int) -> None:
    if limit <= 0 or not docs:
        return
    ranked = sorted(
        docs,
        key=lambda d: (d["task_s"] is None, -(d["task_s"] or 0), -(d["wall_s"] or 0)),
    )[:limit]
    print()
    print(f"Documenti più lenti (top {len(ranked)} per task_s)")
    print(f"{'task':>8}  {'wall':>8}  {'run':<8}  {'dataset':<12}  name")
    print(f"{'-'*8}  {'-'*8}  {'-'*8}  {'-'*12}  {'-'*24}")
    for doc in ranked:
        print(
            f"{fmt_s(doc['task_s']):>8}  {fmt_s(doc['wall_s']):>8}  {doc['run']:<8}  "
            f"{doc['dataset']:<12}  {doc['name']}"
        )


def build_row(dataset_name: str, stats: dict[str, Any]) -> dict[str, Any]:
    by_run = stats["by_run"]
    done = by_run.get("DONE", 0)
    fail = by_run.get("FAIL", 0)
    other = stats["fetched"] - done - fail
    task = stats["task"]
    wall = stats["wall"]
    stages = stats["stages"]
    return {
        "dataset": dataset_name,
        "fetched": stats["fetched"],
        "done": done,
        "fail": fail,
        "other": other,
        "missing_task_s": stats["missing_task_s"],
        "task_sum": task["sum"] if task["count"] else None,
        "task_avg": task["avg"],
        "task_p50": task["p50"],
        "task_p95": task["p95"],
        "task_max": task["max"],
        "wall_p50": wall["p50"],
        "wall_p95": wall["p95"],
        "ocr_p50": stages["ocr"]["p50"],
        "layout_p50": stages["layout"]["p50"],
        "table_p50": stages["table"]["p50"],
        "embed_p50": stages["embedding"]["p50"],
        "index_p50": stages["indexing"]["p50"],
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Statistiche tempi di ingestion RAGFlow (Task done vs wall-clock)."
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("RAGFLOW_BASE_URL", DEFAULT_BASE_URL),
        help="Base URL RAGFlow (default: RAGFLOW_BASE_URL o URL interno LAN)",
    )
    parser.add_argument(
        "--dataset",
        action="append",
        default=[],
        help="Filtra per nome dataset (ripetibile). Default: tutti.",
    )
    parser.add_argument("--json", action="store_true", help="Output JSON invece della tabella.")
    parser.add_argument(
        "--html",
        nargs="?",
        const=str(Path(__file__).with_name("ingestion-report.html")),
        default=None,
        help="Scrive un report HTML (default: scripts/ragflow/ingestion-report.html).",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Quanti documenti più lenti stampare (0=nessuno). Default: 10.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    api_key = os.environ.get("RAGFLOW_API_KEY", "").strip()
    if not api_key:
        print(
            "RAGFLOW_API_KEY non impostata. Esporta la stessa chiave del MCP ragflow-local.",
            file=sys.stderr,
        )
        return 2

    client = RagflowClient(args.base_url, api_key)
    datasets = client.list_datasets()
    if not datasets:
        print("Nessun dataset trovato.", file=sys.stderr)
        return 1

    wanted = {name.lower() for name in args.dataset}
    if wanted:
        datasets = [ds for ds in datasets if (ds.get("name") or "").lower() in wanted]
        missing = wanted - {(ds.get("name") or "").lower() for ds in datasets}
        if missing:
            print(f"Dataset non trovati: {', '.join(sorted(missing))}", file=sys.stderr)
            return 1

    report_datasets = []
    all_parsed: list[dict[str, Any]] = []
    table_rows = []
    profiles = []
    mismatches = []

    for ds in datasets:
        name = ds.get("name") or ds.get("id")
        ds_id = ds["id"]
        expected = ds.get("document_count")
        docs = client.list_documents(ds_id)
        parsed = [parse_document(name, ds_id, doc) for doc in docs]
        stats = aggregate_docs(parsed)
        if expected is not None and stats["fetched"] != expected:
            mismatches.append(f"{name}: fetched={stats['fetched']} document_count={expected}")
        profile = dataset_profile(ds)
        entry = {
            "name": name,
            "id": ds_id,
            "document_count_api": expected,
            "profile": profile,
            **stats,
        }
        report_datasets.append(entry)
        table_rows.append(build_row(name, stats))
        profiles.append(profile)
        all_parsed.extend(parsed)

    top_docs = (
        sorted(
            all_parsed,
            key=lambda d: (d["task_s"] is None, -(d["task_s"] or 0), -(d["wall_s"] or 0)),
        )[: args.top]
        if args.top > 0
        else []
    )

    if args.html:
        html_path = str(Path(args.html).expanduser().resolve())
        write_report(
            html_path,
            {
                "base_url": args.base_url.rstrip("/"),
                "table_rows": table_rows,
                "profiles": profiles,
                "top": top_docs,
                "mismatches": mismatches,
            },
        )
        print(f"Report HTML: {html_path}")

    if args.json:
        payload = {
            "base_url": args.base_url.rstrip("/"),
            "datasets": report_datasets,
            "mismatches": mismatches,
            "top": top_docs,
        }
        json.dump(payload, sys.stdout, indent=2, default=str)
        print()
    else:
        print(
            "Tempi di ingestion RAGFlow. task_* = somma Task done (Xs) in progress_msg; "
            "wall_* = process_duration (coda/retry inclusi)."
        )
        print()
        print_table(table_rows)
        print_stage_table(table_rows)
        print_top(all_parsed, args.top)
        if mismatches:
            print()
            print("Avviso: mismatch fetched vs document_count dataset:")
            for item in mismatches:
                print(f"  - {item}")

    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
