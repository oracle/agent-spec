#
# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""
Cross-Runtime JUnit Comparison Report

- Reads four JUnit XML files (one per runtime).
- Generates:
  - conformance_tests_report/runtimes_conformance_test_results.html  (HTML dashboard)
  - conformance_tests_report/runtimes_conformance_test_results.csv   (CSV matrix)

Features:
- Overall per-runtime summary (Tests, Pass, Fail, Error, Skipped, Time)
- Module breakdown table per runtime (counts by module)
- Detailed test-by-runtime matrix with colors and error/failure details
- Robust HTML escaping and message truncation for readability
- Standard-library only
"""

import csv
import html
import os
import sys
import xml.etree.ElementTree as ET  # nosec B405
from collections import OrderedDict, defaultdict
from dataclasses import dataclass
from typing import Dict
from typing import OrderedDict as _OrderedDict
from typing import Set, Tuple

# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------

RUNTIMES: _OrderedDict[str, str] = OrderedDict(
    [
        ("WayFlow", "conformance_tests_report/report_WayFlow.xml"),
        ("AutoGen", "conformance_tests_report/report_AutoGen.xml"),
        ("CrewAI", "conformance_tests_report/report_CrewAI.xml"),
        ("LangGraph", "conformance_tests_report/report_LangGraph.xml"),
        ("AgentFramework", "conformance_tests_report/report_AgentFramework.xml"),
        ("OpenAIAgents", "conformance_tests_report/report_OpenAIAgents.xml"),
    ]
)

OUT_DIR = "conformance_tests_report"
CSV_OUT = os.path.join(OUT_DIR, "runtimes_conformance_test_results.csv")
HTML_OUT = os.path.join(OUT_DIR, "runtimes_conformance_test_results.html")

# How we infer "module" from a testcase classname.
# Example classname: tests.validation.clienttools.test_valid_configs_agent_with_1_clienttool
# We will use the first 3 segments (e.g., "tests.validation.clienttools") to reflect modularity.
MODULE_DEPTH = 3

# Colors used in the HTML table for status highlighting
COLORS = {
    "pass": "#e6ffed",  # green
    "fail": "#ffeef0",  # red
    "error": "#fff5e6",  # orange
    "skipped": "#f2f2f2",  # grey
    "n/a": "#f9f9f9",  # light grey
}


# ------------------------------------------------------------------------------
# Data structures
# ------------------------------------------------------------------------------


@dataclass
class TestResult:
    classname: str
    name: str
    status: str  # pass | fail | error | skipped | n/a
    time: float
    message: str = ""


@dataclass
class RuntimeSummary:
    tests: int = 0
    failures: int = 0
    errors: int = 0
    skipped: int = 0
    time: float = 0.0

    def passed(self) -> int:
        return max(0, self.tests - self.failures - self.errors - self.skipped)


# ------------------------------------------------------------------------------
# Parsing JUnit XML
# ------------------------------------------------------------------------------


def parse_junit(file_path: str) -> Tuple[Dict[str, TestResult], RuntimeSummary]:
    """
    Parse a JUnit XML file and return:
      - tests: mapping test_id -> TestResult
      - summary: RuntimeSummary
    test_id convention: f"{classname}::{name}"
    """
    results: Dict[str, TestResult] = {}
    summary = RuntimeSummary()

    if not os.path.exists(file_path):
        print(f"[WARN] File not found: {file_path}", file=sys.stderr)
        return results, summary

    try:
        tree = ET.parse(file_path)  # nosec B314
        root = tree.getroot()
    except Exception as e:
        print(f"[ERROR] Failed parsing {file_path}: {e}", file=sys.stderr)
        return results, summary

    # Support both <testsuite> root and <testsuites>/<testsuite>
    if root.tag == "testsuite":
        suites = [root]
    else:
        suites = root.findall(".//testsuite")

    for suite in suites:
        summary.tests += int(suite.attrib.get("tests", 0))
        summary.failures += int(suite.attrib.get("failures", 0))
        summary.errors += int(suite.attrib.get("errors", 0))
        summary.skipped += int(suite.attrib.get("skipped", 0))
        try:
            summary.time += float(suite.attrib.get("time", 0.0))
        except Exception:
            pass  # nosec B110

        for tc in suite.findall("testcase"):
            classname = tc.attrib.get("classname", "")
            name = tc.attrib.get("name", "")
            time_val = float(tc.attrib.get("time", 0.0))

            test_id = f"{classname}::{name}"

            status = "pass"
            message = ""
            failure = tc.find("failure")
            error = tc.find("error")
            skipped = tc.find("skipped")

            if failure is not None:
                status = "fail"
                message = (failure.attrib.get("message", "") or "") + "\n" + (failure.text or "")
            elif error is not None:
                status = "error"
                message = (error.attrib.get("message", "") or "") + "\n" + (error.text or "")
            elif skipped is not None:
                status = "skipped"
                message = (skipped.attrib.get("message", "") or "") + "\n" + (skipped.text or "")

            results[test_id] = TestResult(
                classname=classname,
                name=name,
                status=status,
                time=time_val,
                message=(message or "").strip(),
            )

    return results, summary


# ------------------------------------------------------------------------------
# Aggregation helpers
# ------------------------------------------------------------------------------


def module_of(classname: str, depth: int = MODULE_DEPTH) -> str:
    if not classname:
        return ""
    parts = classname.split(".")
    if len(parts) <= depth:
        return ".".join(parts)
    return ".".join(parts[:depth])


def truncate_text(s: str, limit: int = 600) -> str:
    s = (s or "").strip()
    if len(s) <= limit:
        return s
    return s[:limit] + "... [truncated]"


def build_matrix_and_summaries(
    runtimes: _OrderedDict[str, str],
) -> Tuple[
    _OrderedDict[str, Dict[str, TestResult]],
    Dict[str, RuntimeSummary],
    Dict[str, Dict[str, Dict[str, int]]],
    Dict[str, Dict[str, str]],
]:
    """
    Returns:
      matrix: Ordered mapping test_id -> row with per-runtime TestResult or n/a
      summaries: mapping runtime -> RuntimeSummary
      modules: mapping module -> mapping runtime -> dict(counts by status)
      test_metadata: mapping test_id -> dict with classname, module, name
    """
    # Parse each runtime
    runtime_results: Dict[str, Dict[str, TestResult]] = {}
    summaries: Dict[str, RuntimeSummary] = {}
    all_test_ids: Set[str] = set()

    for rt_name, path in runtimes.items():
        tests, summary = parse_junit(path)
        runtime_results[rt_name] = tests
        summaries[rt_name] = summary
        all_test_ids.update(tests.keys())

    # Build matrix
    matrix: OrderedDict[str, Dict[str, TestResult]] = OrderedDict()
    test_metadata: Dict[str, Dict[str, str]] = {}
    for test_id in sorted(all_test_ids):
        row: Dict[str, TestResult] = {}
        # keep class/name/module for display
        any_res = None
        for rt_name in runtimes.keys():
            res = runtime_results[rt_name].get(test_id)
            if res is None:
                row[rt_name] = TestResult(classname="", name="", status="n/a", time=0.0, message="")
            else:
                row[rt_name] = res
                any_res = any_res or res
        matrix[test_id] = row
        if any_res:
            test_metadata[test_id] = {
                "classname": any_res.classname,
                "module": module_of(any_res.classname),
                "name": any_res.name,
            }
        else:
            test_metadata[test_id] = {"classname": "", "module": "", "name": ""}

    # Build per-module breakdown
    modules: Dict[str, Dict[str, Dict[str, int]]] = defaultdict(
        lambda: {
            rt: {"pass": 0, "fail": 0, "error": 0, "skipped": 0, "n/a": 0} for rt in runtimes.keys()
        }
    )
    for test_id, row in matrix.items():
        m = test_metadata[test_id]["module"]
        for rt in runtimes.keys():
            status = row[rt].status
            modules[m][rt][status] = modules[m][rt].get(status, 0) + 1

    return matrix, summaries, modules, test_metadata


# ------------------------------------------------------------------------------
# CSV output
# ------------------------------------------------------------------------------


def write_csv(
    matrix: _OrderedDict[str, Dict[str, TestResult]],
    runtimes: _OrderedDict[str, str],
    csv_path: str,
) -> None:
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)

    headers = ["test_id", "classname", "module", "name"] + [
        f"{rt} Status" for rt in runtimes.keys()
    ]
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for test_id, row in matrix.items():
            # infer meta from any runtime
            any_rt = next(iter(runtimes.keys()))
            classname = row[any_rt].classname
            name = row[any_rt].name
            module = module_of(classname)
            statuses = [row[rt].status for rt in runtimes.keys()]
            writer.writerow([test_id, classname, module, name] + statuses)

    print(f"[INFO] Wrote CSV: {csv_path}")


# ------------------------------------------------------------------------------
# HTML output
# ------------------------------------------------------------------------------


def cell_html_for_status(res: TestResult) -> str:
    color = COLORS.get(res.status, "#ffffff")
    # Escape & truncate message for tooltip-like detail
    msg = html.escape(truncate_text(res.message, 800))
    content = f"{res.status.upper()}<br><span style='color:#666;font-size:12px'>time: {res.time:.3f}s</span>"
    if msg:
        content += f"<div class='msg'>{msg}</div>"
    return f"<td style='background:{color}' class='cell'>{content}</td>"


def html_summary_table(summaries: Dict[str, RuntimeSummary]) -> str:
    rows = []
    header = "<tr><th>Runtime</th><th>Tests</th><th>Pass</th><th>Fail</th><th>Error</th><th>Skipped</th><th>Time (s)</th></tr>"
    for rt, s in summaries.items():
        rows.append(
            f"<tr>"
            f"<td>{rt}</td>"
            f"<td class='num'>{s.tests}</td>"
            f"<td class='num pass'>{s.passed()}</td>"
            f"<td class='num fail'>{s.failures}</td>"
            f"<td class='num error'>{s.errors}</td>"
            f"<td class='num skipped'>{s.skipped}</td>"
            f"<td class='num'>{s.time:.2f}</td>"
            f"</tr>"
        )
    return f"<table><thead>{header}</thead><tbody>{''.join(rows)}</tbody></table>"


def html_module_breakdown(
    modules: Dict[str, Dict[str, Dict[str, int]]], runtimes: _OrderedDict[str, str]
) -> str:
    # Headers: Module + for each runtime we show Pass / Fail / Error / Skipped
    # To keep it compact but readable, each runtime is one cell with "P/F/E/S"
    header_cells = "".join([f"<th class='rtcol'>{rt}</th>" for rt in runtimes.keys()])
    header = f"<tr><th>Module</th>{header_cells}</tr>"

    rows = []
    for module in sorted(modules.keys(), key=lambda m: (m == "", m)):  # empty last
        cells = []
        for rt in runtimes.keys():
            c = modules[module][rt]
            cell = (
                f"<div><span class='badge pass'>P {c.get('pass', 0)}</span> "
                f"<span class='badge fail'>F {c.get('fail', 0)}</span> "
                f"<span class='badge error'>E {c.get('error', 0)}</span> "
                f"<span class='badge skipped'>S {c.get('skipped', 0)}</span></div>"
            )
            cells.append(f"<td class='rtcol'>{cell}</td>")
        mod_label = module if module else "<i>(unclassified)</i>"
        rows.append(f"<tr><td class='module'>{mod_label}</td>{''.join(cells)}</tr>")

    return (
        f"<table class='module-table'><thead>{header}</thead><tbody>{''.join(rows)}</tbody></table>"
    )


def html_test_matrix(
    matrix: _OrderedDict[str, Dict[str, TestResult]],
    test_meta: Dict[str, Dict[str, str]],
    runtimes: _OrderedDict[str, str],
) -> str:
    head_cols = "".join([f"<th class='sticky rtcol'>{rt}</th>" for rt in runtimes.keys()])
    rows_html = []
    for test_id, row in matrix.items():
        meta = test_meta.get(test_id, {})
        display_test = html.escape(test_id)
        display_cls = html.escape(meta.get("classname", ""))
        display_mod = html.escape(meta.get("module", ""))
        display_name = html.escape(meta.get("name", ""))
        left = (
            f"<td class='sticky-left'>"
            f"<div class='testid'><code>{display_test}</code></div>"
            f"<div class='meta'><b>module:</b> {display_mod} &nbsp;&nbsp; <b>class:</b> {display_cls} &nbsp;&nbsp; <b>name:</b> {display_name}</div>"
            f"</td>"
        )
        cells = "".join([cell_html_for_status(row[rt]) for rt in runtimes.keys()])
        rows_html.append(f"<tr>{left}{cells}</tr>")

    return f"""
    <table class='matrix'>
      <thead>
        <tr>
          <th class='sticky'>Test</th>
          {head_cols}
        </tr>
      </thead>
      <tbody>
        {''.join(rows_html)}
      </tbody>
    </table>
    """


def write_html(
    matrix: _OrderedDict[str, Dict[str, TestResult]],
    summaries: Dict[str, RuntimeSummary],
    modules: Dict[str, Dict[str, Dict[str, int]]],
    test_meta: Dict[str, Dict[str, str]],
    runtimes: _OrderedDict[str, str],
    html_path: str,
) -> None:
    os.makedirs(os.path.dirname(html_path), exist_ok=True)

    legend = (
        "<div class='legend'><b>Legend:</b> "
        "<span class='lg pass'>PASS</span>, "
        "<span class='lg fail'>FAIL</span>, "
        "<span class='lg error'>ERROR</span>, "
        "<span class='lg skipped'>SKIPPED</span>, "
        "N/A (not present in runtime)"
        "</div>"
    )

    files_list = ", ".join([html.escape(p) for p in runtimes.values()])

    html_doc = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Cross-Runtime Test Comparison</title>
  <style>
    body {{ font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 20px; color: #1f2328; }}
    h1, h2 {{ margin: 0 0 10px 0; }}
    .section {{ margin-bottom: 28px; }}
    .legend {{ margin: 10px 0 18px 0; color: #444; }}
    .lg.pass {{ background: {COLORS['pass']}; padding: 2px 6px; border-radius: 4px; }}
    .lg.fail {{ background: {COLORS['fail']}; padding: 2px 6px; border-radius: 4px; }}
    .lg.error {{ background: {COLORS['error']}; padding: 2px 6px; border-radius: 4px; }}
    .lg.skipped {{ background: {COLORS['skipped']}; padding: 2px 6px; border-radius: 4px; }}

    table {{ border-collapse: collapse; width: 100%; table-layout: fixed; }}
    th, td {{ border: 1px solid #ddd; padding: 6px 8px; vertical-align: top; word-wrap: break-word; }}
    th {{ background: #fafafa; }}
    .num {{ text-align: right; }}
    .pass {{ color: #116329; }}
    .fail {{ color: #cf222e; }}
    .error {{ color: #9a6700; }}
    .skipped {{ color: #57606a; }}

    /* Summary table */
    .summary th, .summary td {{ font-size: 14px; }}
    .summary .pass, .summary .fail, .summary .error, .summary .skipped {{ font-weight: 600; }}

    /* Module breakdown */
    .module-table .module {{ white-space: nowrap; }}
    .badge {{ display: inline-block; margin: 2px 4px; padding: 1px 6px; border-radius: 10px; background: #f6f8fa; border: 1px solid #d0d7de; }}
    .badge.pass {{ border-color: #2da44e; }}
    .badge.fail {{ border-color: #d1242f; }}
    .badge.error {{ border-color: #bf8700; }}
    .badge.skipped {{ border-color: #868e96; }}
    .rtcol {{ text-align: center; }}

    /* Sticky headers and first column in matrix */
    .matrix th.sticky {{ position: sticky; top: 0; z-index: 3; }}
    .matrix th.rtcol {{ position: sticky; top: 0; z-index: 2; }}
    .matrix td.sticky-left {{ position: sticky; left: 0; background: #fff; z-index: 4; width: 40%; max-width: 600px; }}
    .matrix .testid {{ font-size: 13px; margin-bottom: 4px; }}
    .matrix .meta {{ font-size: 12px; color: #57606a; }}
    .cell .msg {{ margin-top: 6px; max-width: 700px; white-space: pre-wrap; color: #555; font-size: 12px; }}
    .files {{ color: #57606a; font-size: 12px; }}

    /* Section spacing */
    .spacer {{ height: 8px; }}

  </style>
</head>
<body>
  <h1>Cross-Runtime Test Comparison</h1>
  <div class="files">Files compared: {files_list}</div>
  {legend}

  <div class="section summary">
    <h2>Overall Summary</h2>
    {html_summary_table(summaries)}
  </div>

  <div class="section">
    <h2>Module Breakdown</h2>
    <div class="spacer"></div>
    {html_module_breakdown(modules, runtimes)}
  </div>

  <div class="section">
    <h2>Detailed Test Matrix</h2>
    <div class="spacer"></div>
    {html_test_matrix(matrix, test_meta, runtimes)}
  </div>
</body>
</html>
"""
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_doc)
    print(f"[INFO] Wrote HTML: {html_path}")


# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------


def main() -> None:
    matrix, summaries, modules, test_meta = build_matrix_and_summaries(RUNTIMES)
    write_csv(matrix, RUNTIMES, CSV_OUT)
    write_html(matrix, summaries, modules, test_meta, RUNTIMES, HTML_OUT)


if __name__ == "__main__":
    main()
