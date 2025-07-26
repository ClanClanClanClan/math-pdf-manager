"""
Reporter – HTML + CSV generator for the filename-checker tool-chain
────────────────────────────────────────────────────────────────────
Exports
-------
• strip_latex_for_display(...)
• sanitize_report_data(...)
• prepare_duplicates_for_report(...)
• generate_html_report(...)
• generate_csv_report(...)
• _BUNDLED_TEMPLATE  ← fallback Jinja template (always present)
"""
from __future__ import annotations

# ─── std-lib ─────────────────────────────────────────────────────
import csv
import json
import logging
import textwrap
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional

# ─── 3rd-party ───────────────────────────────────────────────────
import regex as re                      # better \p{} support than std re
from jinja2 import (
    Environment,
    FileSystemLoader,
    Template,
    UndefinedError,
    select_autoescape,
)

logger = logging.getLogger("reporter")

# ═════════════════════════════════════════════════════════════════
# 1.  TeX / LaTeX stripper (keeps output CSV/HTML-safe)
# ═════════════════════════════════════════════════════════════════
_LATEX_MATH_RE = re.compile(r"\$.*?\$", re.DOTALL)
_LATEX_CMD_RE  = re.compile(r"\\[A-Za-z]+(?:\\s*\\{[^}]*\\}, flags=re.UNICODE)?")


def strip_latex_for_display(text: str) -> str:
    """Remove inline math ($…$) *and* simple TeX commands."""
    if not text:
        return ""
    text = _LATEX_MATH_RE.sub("", text)
    text = _LATEX_CMD_RE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()

# ═════════════════════════════════════════════════════════════════
# 2.  Sanitiser & extra-issue merger
# ═════════════════════════════════════════════════════════════════
def _sanitize_field(val: str | List[str]) -> str | List[str]:
    if isinstance(val, list):
        return [strip_latex_for_display(x) for x in val]
    return strip_latex_for_display(val)


def sanitize_report_data(
    filename_checks : List[Dict[str, Any]],
    extra_issues    : Optional[Dict[str, List[str]]] = None,
) -> None:
    """Mutate *filename_checks* in-place – strips TeX, merges extra issues."""
    for row in filename_checks:
        for key in ("filename", "fixed_filename", "path", "folder"):
            if key in row:
                row[key] = _sanitize_field(row[key])         # type: ignore[arg-type]
        for key in ("errors", "suggestions"):
            if key in row and row[key]:
                row[key] = _sanitize_field(row[key])         # type: ignore[arg-type]

    if extra_issues:
        by_name = {row["filename"]: row for row in filename_checks}
        for fname, probs in extra_issues.items():
            clean = strip_latex_for_display(fname)
            row   = by_name.get(clean)
            if not row:
                filename_checks.append(
                    {
                        "filename"      : clean,
                        "errors"        : _sanitize_field(probs),
                        "suggestions"   : [],
                        "fixed_filename": "",
                    }
                )
                continue
            row.setdefault("errors", [])
            row["errors"].extend(strip_latex_for_display(p) for p in probs)

# ═════════════════════════════════════════════════════════════════
# 3.  Duplicate-groups helper
# ═════════════════════════════════════════════════════════════════
def prepare_duplicates_for_report(dupes: List[List[str]]) -> List[List[str]]:
    """Return a shallow copy that is safe for Jinja iteration."""
    return [list(g) for g in dupes]

# ═════════════════════════════════════════════════════════════════
# 4.  Built-in fallback HTML template   (▸ metadata always shown)
# ═════════════════════════════════════════════════════════════════
_BUNDLED_TEMPLATE: str = textwrap.dedent(
    """\
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>PDF Audit Report</title>
      <style>
        body{font-family:system-ui,Arial,sans-serif;margin:0;background:#f5f7fa;color:#222}
        header{background:#05385B;color:#fff;padding:1em 2em}
        main{max-width:900px;margin:2em auto;padding:0 1.2em}
        .file,.dupe{background:#fff;border-radius:6px;padding:0.8em 1em;margin:1em 0;box-shadow:0 1px 6px #0002}
        .error{color:#c00}.suggestion{color:#960}
        pre{white-space:pre-wrap;font-size:0.9em;background:#f2f4f5;padding:0.6em;border-radius:4px;overflow-x:auto}
        .metadata{margin-top:.3em;font-size:.95em;line-height:1.3}
      </style>
      <script>
        function downloadCSV(id){
          const c=document.getElementById(id).textContent;
          const b=new Blob([c],{type:'text/csv'});
          const u=URL.createObjectURL(b);
          const a=document.createElement('a');a.href=u;a.download='report.csv';a.click();
          URL.revokeObjectURL(u);}
        function downloadJSON(id){
          const j=document.getElementById(id).textContent;
          const b=new Blob([j],{type:'application/json'});
          const u=URL.createObjectURL(b);
          const a=document.createElement('a');a.href=u;a.download='report.json';a.click();
          URL.revokeObjectURL(u);}
      </script>
    </head>
    <body>
      <header>
        <h1>PDF Audit Report</h1>
        <div class="summary">
          Generated: {{ generated }}
          – files: {{ filename_checks|length }}
          – config: {{ config_hash or 'default' }}
          – version: {{ version or 'n/a' }}
          – user: {{ user or 'unknown' }}
        </div>
        <div>
          <button onclick="downloadCSV('csvdata')">CSV</button>
          <button onclick="downloadJSON('jsondata')">JSON</button>
        </div>
      </header>

      <main>
        {% if duplicates %}
          <h2>Possible duplicates</h2>
          {% for group in duplicates %}
            <div class="dupe">
              <b>Group:</b>
              <ul>{% for f in group %}<li>{{ f }}</li>{% endfor %}</ul>
            </div>
          {% endfor %}
        {% endif %}

        {% for row in filename_checks %}
          {% if row.errors or row.suggestions %}
          <div class="file">
            📄 <b>{{ row.filename }}</b>
            {% if row.errors %}
              <div class="error"><ul>{% for e in row.errors %}<li>{{ e }}</li>{% endfor %}</ul></div>
            {% endif %}
            {% if row.suggestions %}
              <div class="suggestion"><ul>{% for s in row.suggestions %}<li>{{ s }}</li>{% endfor %}</ul></div>
            {% endif %}
            {% if row.fixed_filename and row.fixed_filename != row.filename %}
              <div>➜ Suggested: <b>{{ row.fixed_filename }}</b></div>
            {% endif %}
            {% if metadata_results.get(row.filename) %}
              {% set m = metadata_results[row.filename] %}
              <div class="metadata">
                {% if m.arxiv_id %}arXiv: <b>{{ m.arxiv_id }}</b>{% endif %}
                {% if m.DOI %} · DOI: <b>{{ m.DOI }}</b>{% endif %}
                {% if m.year %} · Year: {{ m.year }}{% endif %}
                {% if m.title %} · Title: {{ m.title }}{% endif %}
                {% if m.authors %} · Authors: {{ m.authors|join(', ') }}{% endif %}
              </div>
            {% endif %}
          </div>
          {% endif %}
        {% endfor %}

        <pre id="csvdata"  style="display:none">{{ csv_content }}</pre>
        <pre id="jsondata" style="display:none">{{ json_content }}</pre>
      </main>
    </body>
    </html>
    """
)

# ═════════════════════════════════════════════════════════════════
# 5.  Misc helpers
# ═════════════════════════════════════════════════════════════════
def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _rows_to_csv(rows: List[Dict[str, Any]]) -> str:
    buf = StringIO()
    w   = csv.DictWriter(
        buf,
        fieldnames=["filename", "fixed_filename", "errors", "suggestions"],
        lineterminator="\n",
    )
    w.writeheader()
    for r in rows:
        w.writerow(
            {
                "filename"      : r.get("filename", ""),
                "fixed_filename": r.get("fixed_filename", ""),
                "errors"        : "; ".join(r.get("errors", [])),
                "suggestions"   : "; ".join(r.get("suggestions", [])),
            }
        )
    return buf.getvalue()

# ═════════════════════════════════════════════════════════════════
# 6.  Public – HTML generator
# ═════════════════════════════════════════════════════════════════
def generate_html_report(
    filename_checks      : List[Dict[str, Any]],
    *,
    duplicates           : Optional[List[List[str]]]      = None,
    output_path          : str | Path                     = "report.html",
    template_dir         : str | Path                     = "templates",
    dry_run              : bool                           = False,
    hide_clean           : bool                           = False,
    extra_issues         : Optional[Dict[str, List[str]]] = None,
    metadata_results     : Optional[Dict[str, Dict[str,Any]]] = None,
    skipped_files        : Optional[List[Dict[str,str]]]  = None,
    skipped_section_title: str                            = "Skipped / Rate-limited / Unprocessed files",
    open_browser         : bool                           = True,
    config_hash          : Optional[str]                  = None,
    version              : Optional[str]                  = None,
    user                 : Optional[str]                  = None,
) -> Path:
    sanitize_report_data(filename_checks, extra_issues)
    duplicates   = duplicates or []
    csv_content  = _rows_to_csv(filename_checks)
    json_content = json.dumps(filename_checks,
                              ensure_ascii=False,
                              indent=2,
                              default=str)

    env = Environment(
        loader     = FileSystemLoader(template_dir),
        autoescape = select_autoescape(["html", "xml"]),
    )
    env.globals["now"] = _timestamp

    try:
        tpl: Template = env.get_template("report_template.html")
    except Exception:
        logger.warning("Custom template not found in %s – using fallback.",
                       template_dir)
        tpl = Environment(autoescape=True).from_string(_BUNDLED_TEMPLATE)

    try:
        html: str = tpl.render(
            filename_checks       = filename_checks,
            duplicates            = prepare_duplicates_for_report(duplicates),
            dry_run               = dry_run,
            metadata_results      = metadata_results or {},
            skipped_files         = skipped_files or [],
            skipped_section_title = skipped_section_title,
            generated             = _timestamp(),
            csv_content           = csv_content,
            json_content          = json_content,
            config_hash           = config_hash,
            version               = version,
            user                  = user,
        )
    except UndefinedError as err:
        logger.error("Template rendering failed: %s", err)
        raise

    out = Path(output_path)
    out.write_text(html, encoding="utf-8")
    logger.info("HTML report written to %s", out)

    if open_browser:
        try:
            import webbrowser

            webbrowser.open(f"file://{out.resolve()}")
        except Exception as exc:                          # pragma: no cover
            logger.warning("Could not open browser: %s", exc)

    return out

# ═════════════════════════════════════════════════════════════════
# 7.  Public – CSV generator
# ═════════════════════════════════════════════════════════════════
def generate_csv_report(
    filename_checks      : List[Dict[str, Any]],
    *,
    output_path          : str | Path                     = "report.csv",
    hide_clean           : bool                           = False,
    skipped_files        : Optional[List[Dict[str, str]]] = None,
    skipped_section_title: str                            = "Skipped / Rate-limited / Unprocessed files",
) -> Path:
    sanitize_report_data(filename_checks)

    out = Path(output_path)
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["filename", "fixed_filename", "errors", "suggestions"],
        )
        w.writeheader()
        for r in filename_checks:
            w.writerow(
                {
                    "filename"      : r.get("filename", ""),
                    "fixed_filename": r.get("fixed_filename", ""),
                    "errors"        : "; ".join(r.get("errors", [])),
                    "suggestions"   : "; ".join(r.get("suggestions", [])),
                }
            )
        if skipped_files:
            f.write("\n" + skipped_section_title.upper() + "\n")
            skip_writer = csv.DictWriter(f,
                                         fieldnames=["path", "type", "reason"])
            skip_writer.writeheader()
            skip_writer.writerows(skipped_files)

    logger.info("CSV report written to %s", out)
    return out

# ═════════════════════════════════════════════════════════════════
# 8.  Manual demo (python reporter.py)
# ═════════════════════════════════════════════════════════════════
if __name__ == "__main__":                              # pragma: no cover
    logging.basicConfig(level=logging.INFO)

    demo_rows = [
        {
            "filename"      : "Smith_-Doe_2024.pdf",
            "folder"        : "/Papers",
            "path"          : "/Papers/Smith_-Doe_2024.pdf",
            "errors"        : ["Bad dash -- use –"],
            "suggestions"   : ["Replace ASCII hyphen"],
            "fixed_filename": "Smith‒Doe_2024.pdf",
        },
        {
            "filename"      : "Good_File.pdf",
            "folder"        : "/Papers",
            "path"          : "/Papers/Good_File.pdf",
            "errors"        : [],
            "suggestions"   : [],
            "fixed_filename": "",
        },
    ]

    generate_html_report(
        demo_rows,
        duplicates=[["dup.pdf", "dup (1).pdf"]],
        metadata_results={
            "Smith_-Doe_2024.pdf": {
                "arxiv_id": "2401.00001",
                "year"    : 2024,
                "source"  : "arxiv",
                "title"   : "α-Enhanced Example",
                "authors" : ["Smith", "Doe"],
            }
        },
        output_path="demo_report.html",
        open_browser=False,
        config_hash="deadbeef",
        version="9.9.9",
        user="demo-user",
    )