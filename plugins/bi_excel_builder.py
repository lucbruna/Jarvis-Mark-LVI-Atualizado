"""JARVIS plugin - build Excel workbooks and Power BI reports, delivered ready.

Excel: a real .xlsx with typed sheets, headers, formatting, optional charts
(openpyxl). Power BI: a modern PBIP project folder (report.json + dataset)
that opens directly in Power BI Desktop, plus an Excel data model as the
source. This is the closest thing to "creating in Power BI" an assistant
can do without a live Power BI tenant login: a complete, editable report
scaffold, not a description of one.

Inputs are intentionally small and structured so a model can fill them:
  - tables: list of {name, columns:[], rows:[[...]]}
  - charts: list of {type, title, x, y, sheet}
  - measures: list of DAX measure strings for Power BI
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from core import outcome

PLUGIN = {
    "name": "bi_excel_builder",
    "description": (
        "Builds an Excel workbook (.xlsx) and/or a Power BI project (.pbip) "
        "from structured data and delivers the files ready to open. Use for "
        "'create an Excel dashboard', 'make a Power BI report', 'build a "
        "spreadsheet with charts'. Provide tables (name, columns, rows), "
        "optional charts, and optional DAX measures. Files are saved and the "
        "folder is opened. If openpyxl is missing, returns install hint."
    ),
    "brief": "Builds Excel (.xlsx) and Power BI (.pbip) files from structured data and opens them.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "title": {"type": "STRING", "description": "Report/workbook title."},
            # `items` is not decoration: Gemini validates the whole declaration
            # and rejects an ARRAY without it ("parameters.properties[].items:
            # missing field"), which fails the Live setup for EVERY tool, not
            # just this one. Typed here so the model fills them correctly.
            "tables": {
                "type": "ARRAY",
                "description": "List of {name, columns:[str], rows:[[values]]}.",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "name":    {"type": "STRING"},
                        "columns": {"type": "ARRAY", "items": {"type": "STRING"}},
                        "rows":    {"type": "ARRAY", "items": {"type": "ARRAY",
                                                                "items": {"type": "STRING"}}},
                    },
                    "required": ["name", "columns"],
                },
            },
            "charts": {
                "type": "ARRAY",
                "description": "List of {type: bar|line|pie, title, sheet, x_col, y_col}.",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "type":  {"type": "STRING"},
                        "title": {"type": "STRING"},
                        "sheet": {"type": "STRING"},
                        "x_col": {"type": "STRING"},
                        "y_col": {"type": "STRING"},
                    },
                },
            },
            "measures": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
                "description": "DAX measure expressions for Power BI.",
            },
            "output": {"type": "STRING", "description": "excel (default), powerbi, or both."},
            "folder": {"type": "STRING", "description": "Target folder (default: documents)."},
            "name": {"type": "STRING", "description": "Base file name without extension."},
        },
        "required": ["title", "tables"],
    },
    "tier": "extra",
}


def _resolve_folder(folder: str) -> Path:
    home = Path.home()
    mapping = {"desktop": home / "Desktop", "documents": home / "Documents",
               "downloads": home / "Downloads", "home": home}
    p = mapping.get((folder or "documents").lower(), Path(folder).expanduser())
    p.mkdir(parents=True, exist_ok=True)
    return p


def _build_excel(path: Path, title: str, tables, charts) -> str:
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.chart import BarChart, LineChart, PieChart, Reference
        from openpyxl.utils import get_column_letter
    except ImportError:
        return "openpyxl not installed. Run: pip install openpyxl"

    wb = openpyxl.Workbook()
    # remove default sheet; we'll create named ones
    if "Sheet" in wb.sheetnames:
        del wb["Sheet"]

    thin = Side(style="thin", color="BFBFBF")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    header_fill = PatternFill("solid", fgColor="1F4E79")
    header_font = Font(bold=True, color="FFFFFF", size=11)

    for t in tables or []:
        sheet_name = (t.get("name") or "Sheet1")[:31]
        ws = wb.create_sheet(title=sheet_name)
        cols = t.get("columns") or []
        rows = t.get("rows") or []
        # title row
        ws["A1"] = title
        ws["A1"].font = Font(bold=True, size=14, color="1F4E79")
        start = 3
        for j, c in enumerate(cols, start=1):
            cell = ws.cell(row=start, column=j, value=c)
            cell.fill = header_fill
            cell.font = header_font
            cell.border = border
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        for i, row in enumerate(rows, start=start + 1):
            for j, v in enumerate(row, start=1):
                cell = ws.cell(row=i, column=j, value=v)
                cell.border = border
        # column widths
        for j in range(1, len(cols) + 1):
            ws.column_dimensions[get_column_letter(j)].width = 16
        ws.freeze_panes = ws.cell(row=start + 1, column=1)

    # charts
    for ch in charts or []:
        sheet = ch.get("sheet")
        if sheet not in wb.sheetnames:
            sheet = wb.sheetnames[0] if wb.sheetnames else None
        if not sheet:
            continue
        ws = wb[sheet]
        # find header row (row 3)
        headers = [ws.cell(row=3, column=c).value for c in range(1, ws.max_column + 1)]
        x_col = ch.get("x_col") or (headers[0] if headers else None)
        y_col = ch.get("y_col") or (headers[1] if len(headers) > 1 else None)
        if x_col not in headers or y_col not in headers:
            continue
        xi = headers.index(x_col) + 1
        yi = headers.index(y_col) + 1
        last = ws.max_row
        data = Reference(ws, min_col=yi, min_row=3, max_row=last)
        cats = Reference(ws, min_col=xi, min_row=4, max_row=last)
        ctype = (ch.get("type") or "bar").lower()
        if ctype == "line":
            chart = LineChart()
        elif ctype == "pie":
            chart = PieChart()
        else:
            chart = BarChart()
        chart.title = ch.get("title") or y_col
        chart.add_data(data, titles_from_data=True)
        if ctype != "pie":
            chart.set_categories(cats)
        ws.add_chart(chart, f"{get_column_letter(ws.max_column + 2)}3")

    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return f"Excel saved: {path}"


def _build_powerbi(path: Path, title: str, tables, measures) -> str:
    # PBIP (Power BI Project) format - opens directly in Power BI Desktop.
    proj_dir = path  # path is a folder
    proj_dir.mkdir(parents=True, exist_ok=True)
    report_dir = proj_dir / "Report"
    dataset_dir = proj_dir / "SemanticModel"
    report_dir.mkdir(exist_ok=True)
    dataset_dir.mkdir(exist_ok=True)

    # .pbip entry
    (proj_dir / f"{title}.pbip").write_text(json.dumps({
        "version": "1.0",
        "artifacts": [
            {"report": {"path": "Report"}},
        ],
        "settings": {"enableAutoRecovery": True},
    }, indent=2), encoding="utf-8")

    # report.json (PBIR)
    (report_dir / "report.json").write_text(json.dumps({
        "name": title,
        "layoutOptimization": "None",
    }, indent=2), encoding="utf-8")

    # pages folder
    pages = report_dir / "definition" / "pages"
    pages.mkdir(parents=True, exist_ok=True)
    (pages / "page1.json").write_text(json.dumps({
        "name": "page1",
        "displayName": "Overview",
        "width": 1280,
        "height": 720,
    }, indent=2), encoding="utf-8")

    # dataset tables -> TMDL-ish: write a measures.tmdl
    tmdl_dir = dataset_dir / "definition" / "tables"
    tmdl_dir.mkdir(parents=True, exist_ok=True)
    for t in tables or []:
        cols = t.get("columns") or []
        name = t.get("name") or "Table"
        body = f"table '{name}'\n"
        for c in cols:
            body += f"\tcolumn '{c}'\n\t\tdataType: string\n"
        body += "\n"
        (tmdl_dir / f"{name}.tmdl").write_text(body, encoding="utf-8")

    # measures
    if measures:
        mbody = "table 'Measures'\n"
        for m in measures:
            mbody += f"\tmeasure '{m}' = {m}\n"
        (tmdl_dir / "Measures.tmdl").write_text(mbody, encoding="utf-8")

    # save the data as csv alongside so PB can import
    try:
        import csv
        for t in tables or []:
            with open(proj_dir / f"{t.get('name','table')}.csv", "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(t.get("columns") or [])
                for r in (t.get("rows") or []):
                    w.writerow(r)
    except Exception:
        pass

    return f"Power BI project saved: {proj_dir}"


def _reveal(path: Path) -> None:
    try:
        if sys.platform.startswith("win"):
            subprocess.run(["explorer", str(path)], check=False)
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except Exception:
        pass


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    title = (params.get("title") or "Report").strip()
    tables = params.get("tables") or []
    charts = params.get("charts") or []
    measures = params.get("measures") or []
    output = (params.get("output") or "excel").lower()
    folder = params.get("folder") or "documents"
    base = (params.get("name") or title.replace(" ", "_"))[:40]

    out_dir = _resolve_folder(folder)
    stamp = int(time.time())
    results = []

    if output in ("excel", "both"):
        xlsx = out_dir / f"{base}_{stamp}.xlsx"
        msg = _build_excel(xlsx, title, tables, charts)
        results.append(msg)
        if "not installed" not in msg:
            threading.Thread(target=_reveal, args=(xlsx,), daemon=True).start()

    if output in ("powerbi", "both"):
        pbip = out_dir / f"{base}_{stamp}_pbip"
        msg = _build_powerbi(pbip, title, tables, measures)
        results.append(msg)
        threading.Thread(target=_reveal, args=(pbip,), daemon=True).start()

    msg = "\n".join(results)
    if player:
        try:
            player.write_log(f"JARVIS: {msg}")
        except Exception:
            pass
    return outcome.done("bi_excel_builder", note=msg[:400])
