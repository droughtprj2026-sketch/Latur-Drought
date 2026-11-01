# -*- coding: utf-8 -*-
"""Figure registry plus INDEX.md / index.html gallery generation."""
from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path

from . import config as C

_REGISTRY: list[dict] = []


def register(section: str, filename: str, caption: str, source: str = "", path: Path | None = None) -> None:
    _REGISTRY.append(
        {
            "section": section,
            "filename": filename,
            "caption": caption,
            "source": source,
            "path": path,
        }
    )


def figures() -> list[dict]:
    return list(_REGISTRY)


def clear() -> None:
    _REGISTRY.clear()


def _by_section() -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for entry in _REGISTRY:
        grouped.setdefault(entry["section"], []).append(entry)
    return grouped


def write_markdown(meta: dict) -> Path:
    path = C.OUT_ROOT / "INDEX.md"
    grouped = _by_section()
    lines = [
        "# Scientific visualization suite",
        "",
        f"Generated {meta.get('generated_at', datetime.now().isoformat(timespec='seconds'))}",
        "",
        "| item | value |",
        "| --- | --- |",
        f"| Study area | {meta.get('district', '')} |",
        f"| Period | {meta.get('period', '')} |",
        f"| Villages | {meta.get('villages', '')} |",
        f"| Tehsils | {meta.get('tehsils', '')} |",
        f"| Village-months | {meta.get('rows', '')} |",
        f"| Figures | {len(_REGISTRY)} |",
        "",
    ]

    for section, entries in grouped.items():
        lines.append(f"## {C.SECTIONS[section]} - {C.SECTION_TITLES[section]}")
        lines.append("")
        for entry in entries:
            rel = f"{C.SECTIONS[section]}/{entry['filename']}"
            lines.append(f"- `{rel}`")
            lines.append(f"  - {entry['caption']}")
            if entry["source"]:
                lines.append(f"  - Data: {entry['source']}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_html(meta: dict) -> Path:
    path = C.OUT_ROOT / "index.html"
    grouped = _by_section()
    parts = [
        "<!doctype html>",
        '<html lang="en"><head><meta charset="utf-8">',
        "<title>Latur drought - scientific visualization suite</title>",
        "<style>",
        ":root{--ink:#1b1b1b;--muted:#666;--line:#e2e2e2;--bg:#fafafa}",
        "*{box-sizing:border-box}",
        "body{margin:0;padding:32px 40px 80px;background:var(--bg);color:var(--ink);"
        "font:15px/1.55 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}",
        "h1{font-size:27px;margin:0 0 6px;letter-spacing:-.02em}",
        ".meta{color:var(--muted);font-size:13px;margin-bottom:26px}",
        ".meta b{color:var(--ink);font-weight:600}",
        "h2{font-size:17px;margin:44px 0 14px;padding-bottom:8px;border-bottom:1px solid var(--line)}",
        ".grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(420px,1fr));gap:26px}",
        "figure{margin:0;background:#fff;border:1px solid var(--line);border-radius:10px;overflow:hidden}",
        "figure img{width:100%;display:block;background:#fff}",
        "figcaption{padding:12px 14px 14px;font-size:12.5px;color:#333;border-top:1px solid var(--line)}",
        "figcaption code{display:block;color:var(--muted);font-size:11px;margin-top:6px}",
        "</style></head><body>",
        "<h1>Drought monitoring - scientific visualization suite</h1>",
        f'<div class="meta">Study area <b>{html.escape(str(meta.get("district", "")))}</b>'
        f' &middot; period <b>{html.escape(str(meta.get("period", "")))}</b>'
        f' &middot; <b>{meta.get("villages", "")}</b> villages'
        f' &middot; <b>{meta.get("tehsils", "")}</b> tehsils'
        f' &middot; <b>{meta.get("rows", "")}</b> village-months'
        f' &middot; <b>{len(_REGISTRY)}</b> figures'
        f' &middot; generated {html.escape(str(meta.get("generated_at", "")))}</div>',
    ]

    for section, entries in grouped.items():
        parts.append(f"<h2>{html.escape(C.SECTIONS[section])} - {html.escape(C.SECTION_TITLES[section])}</h2>")
        parts.append('<div class="grid">')
        for entry in entries:
            rel = f"{C.SECTIONS[section]}/{entry['filename']}"
            parts.append(
                "<figure>"
                f'<img src="{html.escape(rel)}" alt="{html.escape(entry["filename"])}" loading="lazy">'
                f"<figcaption>{html.escape(entry['caption'])}<code>{html.escape(rel)}</code></figcaption>"
                "</figure>"
            )
        parts.append("</div>")

    parts.append("</body></html>")
    path.write_text("\n".join(parts), encoding="utf-8")
    return path
