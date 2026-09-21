#!/usr/bin/env python3
"""Generatore HTML per il report di ingestion RAGFlow (usato da ingestion_stats.py)."""

from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Any
from zoneinfo import ZoneInfo

SERVICE_SIZING = {
    "version": "v0.27.1",
    "namespace": "ragflow-system",
    "url": "https://ragflow-internal.pindaroli.org",
    "source": "solo namespace ragflow-system: Deployment ragflow + STS infinity + STS redis",
    "app_params": [
        ("DOC_ENGINE", "infinity"),
        ("DOC_BULK_SIZE", "4 task paralleli"),
        ("EMBEDDING_BATCH_SIZE", "16"),
        ("TZ", "Europe/Rome"),
    ],
    "totals": {
        "cpu_req": "2.7 vCPU",
        "cpu_lim": "5.5 vCPU",
        "cpu_live": "5 m",
        "mem_req": "5.5 Gi",
        "mem_lim": "11 Gi",
        "mem_live": "5.3 Gi",
        "disk_pvc": "25 Gi",
        "disk_used": "13 Gi",
    },
    "workloads": [
        {
            "name": "ragflow",
            "display": "RAGFlow API + DeepDoc",
            "namespace": "ragflow-system",
            "kind": "Deployment",
            "replicas": "1/1",
            "node": "talos-cp-01",
            "image": "infiniflow/ragflow:v0.27.1",
            "cpu_req": "1500m",
            "cpu_lim": "3000m",
            "cpu_live": "3m",
            "cpu_pct": 0.1,
            "mem_req": "3Gi",
            "mem_lim": "6Gi",
            "mem_live": "4820Mi",
            "mem_pct": 78,
            "disk_pvc": "nessuno (stateless)",
            "disk_class": "—",
            "disk_cap": "—",
            "disk_used": "—",
            "scope": "dedicato",
            "note": "RAM live al 78% del limit: è il pod che tiene DeepDoc in memoria.",
        },
        {
            "name": "ragflow-infinity-0",
            "display": "Infinity (indice vettoriale)",
            "namespace": "ragflow-system",
            "kind": "StatefulSet",
            "replicas": "1/1",
            "node": "talos-cp-02",
            "image": "infiniflow/infinity:v0.7.3-x64-v3",
            "cpu_req": "1000m",
            "cpu_lim": "2000m",
            "cpu_live": "1m",
            "cpu_pct": 0.05,
            "mem_req": "2Gi",
            "mem_lim": "4Gi",
            "mem_live": "645Mi",
            "mem_pct": 16,
            "disk_pvc": "ragflow-infinity",
            "disk_class": "local-postgres (NVMe)",
            "disk_cap": "20 Gi",
            "disk_used": "13 Gi (65% del PVC)",
            "scope": "dedicato",
            "note": "Unica replica. Occupazione misurata su /var/infinity.",
        },
        {
            "name": "ragflow-redis-0",
            "display": "Redis / Valkey (coda task)",
            "namespace": "ragflow-system",
            "kind": "StatefulSet",
            "replicas": "1/1",
            "node": "talos-cp-01",
            "image": "valkey/valkey:8",
            "cpu_req": "200m",
            "cpu_lim": "500m",
            "cpu_live": "1m",
            "cpu_pct": 0.2,
            "mem_req": "512Mi",
            "mem_lim": "1Gi",
            "mem_live": "5Mi",
            "mem_pct": 0.5,
            "disk_pvc": "redis-data-ragflow-redis-0",
            "disk_class": "csi-nfs-stripe-arr-conf",
            "disk_cap": "5 Gi",
            "disk_used": "non misurato sul PVC",
            "scope": "dedicato",
            "note": "Unica replica. --maxmemory 128mb. RAM live 5 Mi.",
        },
    ],
}

POSTGRES_SIZING = {
    "cluster": "postgres-main",
    "namespace": "cnpg-system",
    "image": "postgresql:18.1-system-trixie",
    "instances": 2,
    "cpu_req": "nessuno",
    "cpu_lim": "nessuno",
    "cpu_live": "186 m",
    "mem_req": "nessuno",
    "mem_lim": "nessuno",
    "mem_live": "560 Mi",
    "data_pvc": "100 Gi × 2",
    "wal_pvc": "4 Gi primary + 10 Gi replica",
    "ragflow_db": "rag_flow",
    "ragflow_db_size": "28 MB",
    "all_db_logical": "~642 MB",
    "primary_data_used": "3.3 Gi",
    "instances_rows": [
        {
            "name": "postgres-main-3",
            "role": "primary",
            "node": "talos-cp-01",
            "cpu_live": "177 m",
            "mem_live": "378 Mi",
            "data_pvc": "100 Gi",
            "wal_pvc": "4 Gi",
            "data_used": "3.3 Gi",
        },
        {
            "name": "postgres-main-7",
            "role": "replica",
            "node": "talos-cp-02",
            "cpu_live": "9 m",
            "mem_live": "182 Mi",
            "data_pvc": "100 Gi",
            "wal_pvc": "10 Gi",
            "data_used": "non isolabile (stesso NVMe di Infinity)",
        },
    ],
}


def fmt_s(value: float | None) -> str:
    if value is None:
        return "—"
    if value >= 3600:
        return f"{value / 3600:.1f} h"
    if value >= 60:
        return f"{value / 60:.1f} min"
    return f"{value:.2f} s"


def fmt_int(value: Any) -> str:
    try:
        return f"{int(value):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "—"


def fmt_bool(value: Any) -> str:
    if value is True:
        return "sì"
    if value is False:
        return "no"
    return "—"


def bar_width(value: float | None, ceiling: float) -> float:
    if not value or ceiling <= 0:
        return 0.0
    return max(2.0, min(100.0, 100.0 * value / ceiling))


def flag(parser: dict[str, Any], section: str, key: str) -> Any:
    block = parser.get(section) or {}
    if isinstance(block, dict):
        return block.get(key)
    return None


def dataset_profile(ds: dict[str, Any]) -> dict[str, Any]:
    parser = ds.get("parser_config") or {}
    return {
        "chunk_count": ds.get("chunk_count"),
        "token_num": ds.get("token_num") or ds.get("token_count"),
        "chunk_method": ds.get("chunk_method") or "—",
        "embedding_model_name": ds.get("embedding_model_name") or "—",
        "language": ds.get("language") or "—",
        "layout_recognize": parser.get("layout_recognize") or "—",
        "graphrag": flag(parser, "graphrag", "use_graphrag"),
        "raptor": flag(parser, "raptor", "use_raptor"),
        "create_date": (ds.get("create_date") or "")[:10],
    }


def write_report(path: str, payload: dict[str, Any]) -> None:
    generated = datetime.now(ZoneInfo("Europe/Rome")).strftime("%d/%m/%Y %H:%M")
    rows = payload["table_rows"]
    profiles = payload["profiles"]
    top_docs = payload.get("top") or []
    mismatches = payload.get("mismatches") or []

    docs_ceiling = max((r["fetched"] or 0) for r in rows) or 1
    stage_keys = [
        ("ocr_p50", "OCR"),
        ("layout_p50", "Layout"),
        ("table_p50", "Tabelle"),
        ("embed_p50", "Embedding"),
        ("index_p50", "Indexing"),
    ]

    total_docs = sum(r["fetched"] for r in rows)
    total_done = sum(r["done"] for r in rows)
    total_fail = sum(r["fail"] for r in rows)
    total_chunks = sum(int(p.get("chunk_count") or 0) for p in profiles)
    total_tokens = sum(int(p.get("token_num") or 0) for p in profiles)

    def bar(label: str, value: float | None, ceiling: float, css: str) -> str:
        width = bar_width(value, ceiling)
        return (
            f'<div class="bar-line"><span class="bar-k">{escape(label)}</span>'
            f'<div class="bar-track"><span class="bar {css}" style="width:{width:.1f}%"></span></div>'
            f'<span class="bar-v">{escape(fmt_s(value) if css != "docs" else fmt_int(value))}</span></div>'
        )

    def util_cell(live: str, pct: float | None, kind: str) -> str:
        if pct is None:
            return f"<td class='num'>{escape(live)}</td>"
        width = max(0.0, min(100.0, float(pct)))
        css = "hot" if width >= 70 else "okbar"
        return (
            f"<td class='util'><div class='util-n'>{escape(live)}</div>"
            f"<div class='bar-track'><span class='bar {css}' style='width:{width:.1f}%'></span></div>"
            f"<div class='util-p'>{width:.0f}% del limit {kind}</div></td>"
        )

    k8s_rows = []
    for wl in SERVICE_SIZING["workloads"]:
        k8s_rows.append(
            "<tr>"
            f"<td><strong>{escape(wl['display'])}</strong><div class='muted'>{escape(wl['image'])}</div></td>"
            f"<td>{escape(wl['kind'])}<div class='muted'>{escape(wl['namespace'])}</div></td>"
            f"<td>{escape(wl['replicas'])}<div class='muted'>{escape(wl['node'])}</div></td>"
            f"<td class='num'>{escape(wl['cpu_req'])}<div class='muted'>lim {escape(wl['cpu_lim'])}</div></td>"
            + util_cell(wl["cpu_live"], wl["cpu_pct"], "CPU")
            + f"<td class='num'>{escape(wl['mem_req'])}<div class='muted'>lim {escape(wl['mem_lim'])}</div></td>"
            + util_cell(wl["mem_live"], wl["mem_pct"], "RAM")
            + (
                f"<td>{escape(wl['disk_pvc'])}<div class='muted'>{escape(wl['disk_class'])}</div></td>"
                f"<td class='num'>{escape(wl['disk_cap'])}<div class='muted'>usato {escape(wl['disk_used'])}</div></td>"
                f"<td class='wrap'>{escape(wl['note'])}</td>"
                "</tr>"
            )
        )

    param_items = "".join(
        f"<li><strong>{escape(k)}</strong> {escape(v)}</li>" for k, v in SERVICE_SIZING["app_params"]
    )
    totals = SERVICE_SIZING["totals"]
    pg = POSTGRES_SIZING
    pg_rows = []
    for inst in pg["instances_rows"]:
        pg_rows.append(
            "<tr>"
            f"<td><strong>{escape(inst['name'])}</strong></td>"
            f"<td>{escape(inst['role'])}</td>"
            f"<td>{escape(inst['node'])}</td>"
            f"<td class='num'>{escape(inst['cpu_live'])}</td>"
            f"<td class='num'>{escape(inst['mem_live'])}</td>"
            f"<td class='num'>{escape(inst['data_pvc'])}</td>"
            f"<td class='num'>{escape(inst['wal_pvc'])}</td>"
            f"<td>{escape(inst['data_used'])}</td>"
            "</tr>"
        )

    profile_rows = []
    for row, profile in zip(rows, profiles):
        profile_rows.append(
            "<tr>"
            f"<td><strong>{escape(row['dataset'])}</strong></td>"
            f"<td>{escape(profile['create_date'] or '—')}</td>"
            f"<td>{escape(profile['chunk_method'])}</td>"
            f"<td>{escape(str(profile['layout_recognize']))}</td>"
            f"<td>{escape(fmt_bool(profile['graphrag']))}</td>"
            f"<td>{escape(fmt_bool(profile['raptor']))}</td>"
            f"<td class='num'>{fmt_int(row['fetched'])}</td>"
            f"<td class='num'>{fmt_int(profile['chunk_count'])}</td>"
            f"<td class='num'>{fmt_int(profile['token_num'])}</td>"
            f"<td class='wrap'>{escape(str(profile['embedding_model_name']))}</td>"
            "</tr>"
        )

    stats_rows = []
    for row in rows:
        stats_rows.append(
            "<tr>"
            f"<td><strong>{escape(row['dataset'])}</strong></td>"
            f"<td class='num'>{row['fetched']}</td>"
            f"<td class='num ok'>{row['done']}</td>"
            f"<td class='num {'bad' if row['fail'] else ''}'>{row['fail']}</td>"
            f"<td class='num'>{escape(fmt_s(row['task_sum']))}</td>"
            f"<td class='num'>{escape(fmt_s(row['task_avg']))}</td>"
            f"<td class='num'>{escape(fmt_s(row['task_p50']))}</td>"
            f"<td class='num'>{escape(fmt_s(row['task_p95']))}</td>"
            f"<td class='num'>{escape(fmt_s(row['task_max']))}</td>"
            f"<td class='num'>{escape(fmt_s(row['wall_p50']))}</td>"
            f"<td class='num'>{escape(fmt_s(row['wall_p95']))}</td>"
            "</tr>"
        )

    task_bars = []
    for row in rows:
        task_ceiling = max(row["task_p95"] or 0, row["task_p50"] or 0, 1)
        task_bars.append(
            f'<div class="series"><h4>{escape(row["dataset"])}</h4>'
            + bar("p50", row["task_p50"], task_ceiling, "p50")
            + bar("p95", row["task_p95"], task_ceiling, "p95")
            + "</div>"
        )

    wall_bars = []
    for row in rows:
        wall_mix_ceiling = max(row["task_p50"] or 0, row["wall_p50"] or 0, 1)
        wall_bars.append(
            f'<div class="series"><h4>{escape(row["dataset"])}</h4>'
            + bar("task p50", row["task_p50"], wall_mix_ceiling, "p50")
            + bar("wall p50", row["wall_p50"], wall_mix_ceiling, "wall")
            + "</div>"
        )

    docs_bars = []
    for row in rows:
        docs_bars.append(
            f'<div class="series"><h4>{escape(row["dataset"])}</h4>'
            f'<div class="bar-line"><span class="bar-k">docs</span>'
            f'<div class="bar-track"><span class="bar docs" style="width:{bar_width(row["fetched"], docs_ceiling):.1f}%"></span></div>'
            f'<span class="bar-v">{fmt_int(row["fetched"])} · {row["done"]} done · {row["fail"]} fail</span></div></div>'
        )

    stage_series = []
    for row in rows:
        if all(row[k] is None for k, _ in stage_keys):
            continue
        local_ceiling = max((row[k] or 0) for k, _ in stage_keys) or 1
        lines = "".join(bar(label, row[key], local_ceiling, "stage") for key, label in stage_keys)
        stage_series.append(f'<div class="series"><h4>{escape(row["dataset"])}</h4>{lines}</div>')

    top_rows = []
    for doc in top_docs:
        top_rows.append(
            "<tr>"
            f"<td class='num'>{escape(fmt_s(doc.get('task_s')))}</td>"
            f"<td class='num'>{escape(fmt_s(doc.get('wall_s')))}</td>"
            f"<td>{escape(str(doc.get('run')))}</td>"
            f"<td>{escape(str(doc.get('dataset')))}</td>"
            f"<td class='wrap'>{escape(str(doc.get('name')))}</td>"
            "</tr>"
        )

    mismatch_html = ""
    if mismatches:
        items = "".join(f"<li>{escape(item)}</li>" for item in mismatches)
        mismatch_html = f'<div class="banner warn"><strong>Mismatch conteggi:</strong><ul>{items}</ul></div>'

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>RAGFlow — report ingestion lab</title>
  <style>
    :root {{
      --bg: #f4f1ea;
      --surface: #fffcf6;
      --ink: #1c1915;
      --muted: #6b645a;
      --line: #e2d8c8;
      --p50: #2f6f4e;
      --p95: #c47a12;
      --wall: #6b4ea1;
      --docs: #355f8a;
      --stage: #8a3d3d;
      --ok: #2f6f4e;
      --bad: #a33b2c;
      --shadow: 0 10px 30px rgba(28,25,21,.06);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
      background: var(--bg);
      color: var(--ink);
      line-height: 1.45;
    }}
    header {{
      padding: 36px 28px 20px;
      border-bottom: 1px solid var(--line);
      background: var(--surface);
    }}
    header p {{ margin: 6px 0 0; color: var(--muted); }}
    h1 {{ margin: 0; font-size: 32px; letter-spacing: -.02em; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 28px; }}
    h2 {{ font-size: 22px; margin: 36px 0 8px; }}
    h3 {{ margin: 0 0 8px; font-size: 16px; }}
    h4 {{ margin: 0 0 8px; font-size: 14px; }}
    .lede {{ color: var(--muted); max-width: 72ch; margin: 0 0 20px; }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
      margin: 20px 0 8px;
    }}
    .metric, .card {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 16px;
      box-shadow: var(--shadow);
    }}
    .metric .n {{ font-size: 26px; font-weight: 700; }}
    .metric .l, .muted, .note {{ color: var(--muted); font-size: 13px; }}
    .metric .l {{ line-height: 1.35; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 14px;
    }}
    dl {{ margin: 10px 0; }}
    dl div {{ display: flex; justify-content: space-between; gap: 12px; padding: 4px 0; border-bottom: 1px dotted var(--line); }}
    dt {{ color: var(--muted); }}
    dd {{ margin: 0; text-align: right; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 14px;
      overflow: hidden;
      box-shadow: var(--shadow);
    }}
    th, td {{ padding: 10px 12px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }}
    th {{ font-size: 12px; letter-spacing: .04em; text-transform: uppercase; color: var(--muted); }}
    td.num {{ font-variant-numeric: tabular-nums; text-align: right; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 13px; }}
    td.ok {{ color: var(--ok); }}
    td.bad {{ color: var(--bad); font-weight: 700; }}
    td.wrap {{ word-break: break-word; }}
    .tag {{
      display: inline-block;
      font-size: 11px;
      letter-spacing: .04em;
      text-transform: uppercase;
      padding: 2px 8px;
      border-radius: 99px;
      border: 1px solid var(--line);
    }}
    .tag.dedicato {{ background: #e7f1ea; color: var(--p50); }}
    .tag.condiviso {{ background: #f4ead8; color: #8a5a10; }}
    .tag.esterno {{ background: #ece8f6; color: var(--wall); }}
    td.util {{ min-width: 110px; }}
    .util-n {{ font-variant-numeric: tabular-nums; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 13px; }}
    .util-p {{ font-size: 11px; color: var(--muted); }}
    .bar.okbar {{ background: var(--p50); }}
    .bar.hot {{ background: var(--bad); }}
    .sys-meta {{ font-size: 13px; color: var(--muted); margin: 0 0 12px; }}
    .params {{ display: flex; flex-wrap: wrap; gap: 8px 18px; padding: 0; margin: 0 0 8px; list-style: none; }}
    .params li {{ background: var(--surface); border: 1px solid var(--line); border-radius: 999px; padding: 6px 12px; font-size: 13px; }}
    table.sys th {{ white-space: nowrap; }}
    .legend {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 12px;
    }}
    .legend article {{ padding: 14px 16px; }}
    .swatch {{ display: inline-block; width: 10px; height: 10px; border-radius: 99px; margin-right: 6px; }}
    .s-p50 {{ background: var(--p50); }}
    .s-p95 {{ background: var(--p95); }}
    .s-wall {{ background: var(--wall); }}
    .charts {{ display: grid; grid-template-columns: 1fr; gap: 18px; }}
    @media (min-width: 960px) {{
      .charts-2 {{ grid-template-columns: 1fr 1fr; }}
    }}
    .chart {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 16px;
      box-shadow: var(--shadow);
    }}
    .series {{ margin: 0 0 16px; }}
    .bar-line {{ display: grid; grid-template-columns: 88px 1fr 120px; gap: 8px; align-items: center; margin: 4px 0; }}
    .bar-k, .bar-v {{ font-size: 12px; color: var(--muted); }}
    .bar-v {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .bar-track {{ background: #efe6d6; height: 12px; border-radius: 99px; overflow: hidden; }}
    .bar {{ display: block; height: 100%; border-radius: 99px; }}
    .bar.p50 {{ background: var(--p50); }}
    .bar.p95 {{ background: var(--p95); }}
    .bar.wall {{ background: var(--wall); }}
    .bar.docs {{ background: var(--docs); }}
    .bar.stage {{ background: var(--stage); }}
    .banner {{ padding: 12px 14px; border-radius: 12px; margin: 16px 0; }}
    .warn {{ background: #f8e4d4; }}
    footer {{ color: var(--muted); font-size: 13px; padding: 12px 0 40px; }}
  </style>
</head>
<body>
  <header>
    <h1>RAGFlow · report di ingestion</h1>
    <p>Lab GEMINI · {escape(SERVICE_SIZING["url"])} · snapshot {escape(generated)} · fonte {escape(SERVICE_SIZING["source"])}</p>
  </header>
  <main>
    <section>
      <h2>Dimensionamento Kubernetes</h2>
      <p class="lede">Solo i tre workload del namespace <code>ragflow-system</code>: API+DeepDoc, Infinity, Redis. I numeri sotto sono la <strong>somma di quei tre pod</strong>. Niente Postgres condiviso, niente nodi Talos, niente share NFS padre.</p>
      <p class="sys-meta">Come leggerli: <strong>prenotato</strong> = request Kubernetes (quanto lo scheduler tiene da parte). <strong>tetto</strong> = limit (oltre non può andare). <strong>adesso</strong> = uso live a riposo, senza ingest in corso. Disco = capienza dei due PVC (20+5 Gi); usati 13 Gi su Infinity.</p>
      <div class="metrics">
        <div class="metric"><div class="n">{escape(totals['cpu_req'])}</div><div class="l">CPU prenotata<br>1.5+1.0+0.2</div></div>
        <div class="metric"><div class="n">{escape(totals['cpu_lim'])}</div><div class="l">CPU tetto<br>3+2+0.5</div></div>
        <div class="metric"><div class="n">{escape(totals['cpu_live'])}</div><div class="l">CPU adesso<br>3m+1m+1m</div></div>
        <div class="metric"><div class="n">{escape(totals['mem_req'])}</div><div class="l">RAM prenotata<br>3+2+0.5 Gi</div></div>
        <div class="metric"><div class="n">{escape(totals['mem_lim'])}</div><div class="l">RAM tetto<br>6+4+1 Gi</div></div>
        <div class="metric"><div class="n">{escape(totals['mem_live'])}</div><div class="l">RAM adesso<br>4.8+0.6+0.0 Gi</div></div>
        <div class="metric"><div class="n">{escape(totals['disk_pvc'])}</div><div class="l">Disco PVC<br>20 Infinity + 5 Redis</div></div>
        <div class="metric"><div class="n">{escape(totals['disk_used'])}</div><div class="l">Disco usato<br>solo Infinity misurato</div></div>
      </div>
      <div style="overflow:auto">
      <table class="sys">
        <thead>
          <tr>
            <th>Servizio</th><th>Kind</th><th>Replica / nodo</th>
            <th>CPU prenotata → tetto</th><th>CPU adesso</th>
            <th>RAM prenotata → tetto</th><th>RAM adesso</th>
            <th>PVC</th><th>Capienza / usato</th><th>Note</th>
          </tr>
        </thead>
        <tbody>
          {''.join(k8s_rows)}
        </tbody>
      </table>
      </div>
      <h3 style="margin-top:20px">Parametri applicativi</h3>
      <ul class="params">{param_items}</ul>
    </section>

    <section>
      <h2>PostgreSQL · cluster CNPG usato da RAGFlow</h2>
      <p class="lede">Questo è il dimensionamento del servizio <code>{escape(pg['cluster'])}</code> (namespace <code>{escape(pg['namespace'])}</code>), non dei tre pod RAGFlow. Il cluster è condiviso con altri database. La quota <em>netta</em> di RAGFlow è solo il database <code>{escape(pg['ragflow_db'])}</code>.</p>
      <div class="metrics">
        <div class="metric"><div class="n">{escape(pg['ragflow_db_size'])}</div><div class="l">DB rag_flow<br>occupazione netta RAGFlow</div></div>
        <div class="metric"><div class="n">{pg['instances']}</div><div class="l">Istanze CNPG<br>primary + replica</div></div>
        <div class="metric"><div class="n">{escape(pg['cpu_live'])}</div><div class="l">CPU adesso (somma 2 pod)<br>request/limit: {escape(pg['cpu_req'])}</div></div>
        <div class="metric"><div class="n">{escape(pg['mem_live'])}</div><div class="l">RAM adesso (somma 2 pod)<br>request/limit: {escape(pg['mem_req'])}</div></div>
        <div class="metric"><div class="n">{escape(pg['data_pvc'])}</div><div class="l">PVC dati del servizio<br>{escape(pg['wal_pvc'])}</div></div>
        <div class="metric"><div class="n">{escape(pg['primary_data_used'])}</div><div class="l">Dati fisici sul primary<br>tutti i DB, non solo RAGFlow</div></div>
      </div>
      <p class="sys-meta">Somma logica di tutti i database sull’istanza: {escape(pg['all_db_logical'])}. RAGFlow è 28 MB su quel totale. Image {escape(pg['image'])}. <code>spec.resources</code> del Cluster è vuoto: Kubernetes non prenota CPU/RAM a Postgres.</p>
      <div style="overflow:auto">
      <table class="sys">
        <thead>
          <tr>
            <th>Istanza</th><th>Ruolo</th><th>Nodo</th>
            <th>CPU adesso</th><th>RAM adesso</th>
            <th>PVC dati</th><th>PVC WAL</th><th>Usato sul volume</th>
          </tr>
        </thead>
        <tbody>
          {''.join(pg_rows)}
        </tbody>
      </table>
      </div>
    </section>

    <section>
      <div class="metrics">
        <div class="metric"><div class="n">{fmt_int(total_docs)}</div><div class="l">Documenti</div></div>
        <div class="metric"><div class="n">{fmt_int(total_done)}</div><div class="l">DONE</div></div>
        <div class="metric"><div class="n">{fmt_int(total_fail)}</div><div class="l">FAIL</div></div>
        <div class="metric"><div class="n">{fmt_int(total_chunks)}</div><div class="l">Chunk</div></div>
        <div class="metric"><div class="n">{fmt_int(total_tokens)}</div><div class="l">Token indicizzati</div></div>
        <div class="metric"><div class="n">{escape(SERVICE_SIZING["version"])}</div><div class="l">Image RAGFlow</div></div>
      </div>
      {mismatch_html}
    </section>

    <section>
      <h2>Caratteristiche dei dataset</h2>
      <p class="lede">Parser DeepDOC su tutti. GraphRAG/RAPTOR risultano accesi in config su alcuni dataset, ma i tempi sotto misurano solo parse → chunk → embed → index per documento, non i job di grafo.</p>
      <div style="overflow:auto">
      <table>
        <thead>
          <tr>
            <th>Dataset</th><th>Creato</th><th>Chunk method</th><th>Layout</th>
            <th>GraphRAG</th><th>RAPTOR</th><th>Docs</th><th>Chunk</th><th>Token</th><th>Embedding</th>
          </tr>
        </thead>
        <tbody>
          {''.join(profile_rows)}
        </tbody>
      </table>
      </div>
    </section>

    <section>
      <h2>Legenda delle metriche</h2>
      <p class="lede">Due orologi: <strong>task</strong> è il lavoro vero letto da <code>Task done (Xs)</code> nel log; <strong>wall</strong> è <code>process_duration</code>, che include coda Redis, retry e Ollama giù.</p>
      <div class="legend">
        <article class="card"><h3>docs / done / fail</h3><p>Quanti file nel dataset, quanti finiti, quanti in errore. <code>other</code> sarebbe RUNNING/CANCEL; qui è 0.</p></article>
        <article class="card"><h3><span class="swatch s-p50"></span>p50 (mediana)</h3><p>Metà dei documenti è più veloce, metà più lenta. È il tempo del file <em>tipico</em>, non distorto dai pochi PDF lunghi.</p></article>
        <article class="card"><h3><span class="swatch s-p95"></span>p95 (coda)</h3><p>Il 95% è più veloce di questo valore; solo 1 file su 20 è peggio. Serve per dimensionare, non per descrivere il caso comune.</p></article>
        <article class="card"><h3>avg e max</h3><p>La media sale se hai outlier (es. manuali ASUS). Il max è il singolo peggiore. Se avg &gt; p50, la distribuzione ha una coda lunga.</p></article>
        <article class="card"><h3>task_sum</h3><p>Somma dei tempi di lavoro. Con <code>DOC_BULK_SIZE=4</code> il wall del batch è circa task_sum / 4, non la somma seriale.</p></article>
        <article class="card"><h3><span class="swatch s-wall"></span>wall p50 / p95</h3><p>Quanto il job è rimasto aperto. Su OPNsense wall ≫ task perché 421 file aspettano in coda. Non è costo DeepDoc.</p></article>
        <article class="card"><h3>OCR / layout / tabelle</h3><p>Fasi DeepDoc sui PDF. Assenti sui markdown (trattino). In <code>k8s-lab</code> le tabelle dominano.</p></article>
        <article class="card"><h3>embedding / indexing</h3><p>Embedding = bge-m3 su Ollama. Indexing = scrittura su Infinity. Sui markdown l’indexing è il pezzo più lento.</p></article>
      </div>
    </section>

    <section>
      <h2>Statistiche di ingestion</h2>
      <div style="overflow:auto; margin-bottom: 18px">
      <table>
        <thead>
          <tr>
            <th>Dataset</th><th>docs</th><th>done</th><th>fail</th>
            <th>task_sum</th><th>avg</th><th>p50</th><th>p95</th><th>max</th>
            <th>wall p50</th><th>wall p95</th>
          </tr>
        </thead>
        <tbody>
          {''.join(stats_rows)}
        </tbody>
      </table>
      </div>
      <div class="charts charts-2">
        <div class="chart">
          <h3>Documenti per dataset</h3>
          {''.join(docs_bars)}
        </div>
        <div class="chart">
          <h3>Tempo di lavoro (task) · p50 vs p95</h3>
          <p class="muted">Scala relativa al p95 di quel dataset: la barra verde è quanto è “tipico” rispetto alla coda.</p>
          {''.join(task_bars)}
        </div>
        <div class="chart">
          <h3>Coda: task p50 vs wall p50</h3>
          <p class="muted">Se la barra viola è molto più lunga della verde, il file ha aspettato, non lavorato.</p>
          {''.join(wall_bars)}
        </div>
        <div class="chart">
          <h3>Fasi DeepDoc / indexing (p50)</h3>
          {''.join(stage_series) if stage_series else '<p class="muted">Nessuna fase temporizzata.</p>'}
        </div>
      </div>
    </section>

    <section>
      <h2>Documenti più lenti</h2>
      <p class="lede">Ordinati per tempo di lavoro <code>task</code>. Un FAIL può comunque avere minuti di OCR alle spalle e un wall enorme per i retry.</p>
      <div style="overflow:auto">
      <table>
        <thead><tr><th>task</th><th>wall</th><th>run</th><th>dataset</th><th>documento</th></tr></thead>
        <tbody>
          {''.join(top_rows)}
        </tbody>
      </table>
      </div>
    </section>

    <footer>
      Generato da <code>scripts/ragflow/ingestion_stats.py --html</code>.
      Namespace Kubernetes <code>{escape(SERVICE_SIZING["namespace"])}</code>.
      Non commettere segreti: la API key resta in variabile d'ambiente.
    </footer>
  </main>
</body>
</html>
"""
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(html)
