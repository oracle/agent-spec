# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

# mypy: ignore-errors

"""
Generates a HTML report for the Tau2Bench.
The table contains results for each benchmark task (row) for each tested Adapter (column).
Also adds a per-cell 'Details' link inside the colored box (bottom-left, small text) opening a modal
showing action success states and another modal with the action's conversation.
"""
import argparse
import json
import sys
from html import escape


def parse_args():
    p = argparse.ArgumentParser(description="Render Tau2Bench results to HTML table.")
    p.add_argument(
        "inputs",
        nargs="+",
        help='One or more inputs as "path:Label". Example: results.json:"WayFlowRuntime"',
    )
    p.add_argument("-o", "--output", default="tau2bench_report.html", help="Output HTML file")
    return p.parseArgs() if hasattr(p, "parseArgs") else p.parse_args()


def load_results(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def get_cell_block(sim):
    if not sim:
        return {
            "reward": "n/a",
            "yn": "n/a",
            "duration": "n/a",
            "db_match": "n/a",
            "successful_actions_string": "n/a",
            "termination_reason": "n/a",
            "background_color": "n/a",
            "successful_actions": "n/a",
            "total_actions": "n/a",
            "action_checks": [],
            "messages": [],
        }

    reward = sim.get("reward_info", {}).get("reward", None)
    db = sim.get("reward_info", {}).get("db_check", {})
    db_match = db.get("db_match") if db else None

    action_checks = sim.get("reward_info", {}).get("action_checks", []) or []
    total_actions = len(action_checks) if action_checks else None
    successful_actions = 0
    for action in action_checks:
        if action.get("action_reward", 0) and action["action_reward"] > 0:
            successful_actions += 1

    termination_reason = sim.get("termination_reason", None)
    duration = sim.get("duration", None)

    reward_str = "n/a" if reward is None else f"{reward:.2f}"
    yn_str = "n/a" if reward is None else ("Yes" if reward > 0 else "No")
    duration_str = "n/a" if duration is None else f"{duration:.2f}s"
    if db_match is None:
        db_str = "n/a"
    else:
        db_str = "Yes" if db_match is True else ("No" if db_match is False else "n/a")

    # Background color heuristic
    if successful_actions > 0:
        background_color = "#ffeef0"
    else:
        background_color = "#ffccd0"
    if (reward or 0) > 0:
        background_color = "#fff5e6"
        if total_actions and total_actions == successful_actions:
            background_color = "#e6ffed"

    successful_actions_string = (
        f"{successful_actions}/{total_actions}" if total_actions not in (None, 0) else "n/a"
    )

    return {
        "reward": reward_str,
        "yn": yn_str,
        "duration": duration_str,
        "db_match": db_str,
        "successful_actions_string": successful_actions_string,
        "termination_reason": termination_reason or "n/a",
        "background_color": background_color,
        "successful_actions": successful_actions,
        "total_actions": total_actions if total_actions is not None else "n/a",
        "action_checks": action_checks,
        "messages": sim.get("messages", []) or [],
    }


def pick_simulation_for_task(sims_for_task):
    if not sims_for_task:
        return None
    try:
        sims_for_task = sorted(
            sims_for_task,
            key=lambda s: s.get("timestamp") or s.get("end_time") or "",
        )
    except KeyError:
        pass
    return sims_for_task[-1]


def _serialize_actions_for_attr(action_rows):
    """
    action_rows is a list of dicts with:
      name, action_reward, action_match, conversation (list of {role, content})
    """
    return json.dumps(action_rows or [], ensure_ascii=True)


def _build_actions_payload(sim):
    """
    Build a per-action payload including a compact conversation snippet.
    Conversation extraction heuristic:
      - Find messages with tool_calls that match the action name.
      - For each matching tool call, include:
        - The preceding user/assistant message (if any),
        - The assistant tool-call message,
        - The tool response message (matched by tool id),
        - The following assistant message (if any).
    Falls back to an empty snippet if no match is found.
    """
    actions = []
    action_checks = (sim or {}).get("reward_info", {}).get("action_checks", []) or []
    messages = (sim or {}).get("messages", []) or []

    # Build index for tool response messages by id
    tool_response_by_id = {}
    for m in messages:
        if m.get("role") == "tool" and "id" in m:
            tool_response_by_id[m["id"]] = m

    # Traverse messages to map action name -> snippets
    snippets_by_name = {}
    for idx, m in enumerate(messages):
        tool_calls = m.get("tool_calls") or []
        if not tool_calls:
            continue
        for tc in tool_calls:
            name = tc.get("name")
            if not name:
                continue
            snip = []
            # previous message (context)
            if idx - 1 >= 0:
                pm = messages[idx - 1]
                snip.append({"role": pm.get("role", "n/a"), "content": pm.get("content", "")})
            # the assistant tool-call message
            snip.append(
                {
                    "role": m.get("role", "n/a"),
                    "content": m.get("content") or f"[tool_call: {name}]",
                }
            )
            # the tool response (by id)
            tid = tc.get("id")
            if tid and tid in tool_response_by_id:
                tm = tool_response_by_id[tid]
                snip.append({"role": "tool", "content": tm.get("content", "")})
            # next message (assistant reply after tool)
            if idx + 1 < len(messages):
                nm = messages[idx + 1]
                if nm.get("role") == "assistant":
                    snip.append({"role": "assistant", "content": nm.get("content", "")})
            snippets_by_name.setdefault(name, []).append(snip)

    for ac in action_checks:
        a = ac.get("action", {}) or {}
        name = a.get("name", "n/a")
        conv_snippets = snippets_by_name.get(name, [])
        # Use first snippet if present; else empty
        conv = conv_snippets[0] if conv_snippets else []
        actions.append(
            {
                "name": name,
                "action_reward": ac.get("action_reward", 0),
                "action_match": ac.get("action_match", None),
                "conversation": conv,
            }
        )
    return actions


def build_html_table(runtime_labels, all_task_ids, data_by_runtime_and_task):
    styles = """
        <style>
        :root { --mono: Consolas, "Courier New", monospace; }
        body { font-family: Arial, Helvetica, sans-serif; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ccc; padding: 8px; vertical-align: top; text-align: left; }
        th { background: #f5f5f5; }
        .title { font-size: 20px; font-weight: bold; padding: 8px; }
        .subtable { width: 100%; border-collapse: collapse; table-layout: fixed; }
        .subtable td { border: none; padding: 3px 2px; }
        .runtime-header { font-weight: bold; text-align: center; }
        .mono { font-family: var(--mono); font-size: 12px; }
        .field { font-size: 12px; }
        /* Colored box that contains both the subtable and the Details link */
        .cell-box {
          position: relative;
          border-radius: 4px;
          padding: 2px 2px 10px; /* extra bottom padding so link doesn't overlap text */
          min-height: 90px;      /* ensures enough space to anchor link at bottom */
        }
        /* Bottom-right tiny link */
        .link {
          position: absolute; bottom: 6px; right: 8px;
          color: #1d4ed8; cursor: pointer; text-decoration: underline;
          font-size: 9px;
          font-weight: 700;
        }
        .muted { color: #6b7280; font-size: 11px; }
        /* Modal */
        .modal-backdrop {
          position: fixed; inset: 0; background: rgba(0,0,0,0.45);
          display: none; align-items: center; justify-content: center; z-index: 9999;
        }
        .modal {
          background: #fff; border-radius: 6px; min-width: 420px; max-width: 80vw; max-height: 80vh;
          box-shadow: 0 10px 30px rgba(0,0,0,0.25); overflow: hidden; display: flex; flex-direction: column;
        }
        .modal-header {
          padding: 10px 14px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center;
          background: #f9fafb;
        }
        .modal-title { font-size: 14px; font-weight: bold; }
        .modal-close { cursor: pointer; border: none; background: transparent; font-size: 18px; line-height: 1; }
        .modal-body { padding: 12px; overflow: auto; }
        .actions-table { width: 100%; border-collapse: collapse; }
        .actions-table th, .actions-table td { border: 1px solid #ddd; padding: 6px; font-size: 12px; }
        .ok { color: #15803d; }
        .bad { color: #b91c1c; }
        /* Second modal for conversation */
        .conv-msg { margin: 0 0 8px 0; }
        .conv-role { font-weight: bold; }
        </style>
    """

    # Header row
    header_cells = ['<th style="width: 80px;">Task #</th>']
    for label in runtime_labels:
        header_cells.append(f'<th class="runtime-header">{escape(label)}</th>')
    header_html = "<tr>" + "".join(header_cells) + "</tr>"

    # Body rows
    body_rows = []

    # Averages
    averages = {}
    for label in runtime_labels:
        sims = data_by_runtime_and_task.get(label, {})
        rewards, durations = [], []
        total_successful = 0
        total_actions_sum = 0
        for _, sim in sims.items():
            block = get_cell_block(sim)
            if block["reward"] != "n/a":
                rewards.append(float(block["reward"]))
            if block["duration"] != "n/a":
                durations.append(float(block["duration"][:-1]))
            if block["successful_actions_string"] != "n/a":
                successful, total = block["successful_actions_string"].split("/")
                total_successful += int(successful)
                total_actions_sum += int(total)
        averages[label] = {
            "reward": f"{sum(rewards)/len(rewards):.2f}" if rewards else "n/a",
            "duration": f"{sum(durations)/len(durations):.2f}s" if durations else "n/a",
            "successful_actions": (
                f"{total_successful}/{total_actions_sum}" if total_actions_sum else "n/a"
            ),
        }

    row_cells = ["<td class='mono'>Average</td>"]
    for label in runtime_labels:
        avg = averages[label]
        reward = escape(avg["reward"])
        duration = escape(avg["duration"])
        successful_actions = escape(avg["successful_actions"])
        cell_html = f"""
          <div class="cell-box" style="background-color:#e2e3e5">
            <table class="subtable">
              <tr class="field"><td>Reward</td><td class="mono">{reward}</td></tr>
              <tr class="field"><td>Duration</td><td class="mono">{duration}</td></tr>
              <tr class="field"><td>DB Match</td><td class="mono">n/a</td></tr>
              <tr class="field"><td>Successful Actions</td><td class="mono">{successful_actions}</td></tr>
              <tr class="field"><td>Termination Reason</td><td class="mono">n/a</td></tr>
            </table>
          </div>
        """
        row_cells.append(f"<td>{cell_html}</td>")

    # Individual tasks
    body_rows.append('<tr style="background-color: #e2e3e5">' + "".join(row_cells) + "</tr>")
    for task_id in sorted(all_task_ids, key=lambda x: int(x) if str(x).isdigit() else str(x)):
        row_cells = [f"<td class='mono'>{escape(str(task_id))}</td>"]
        for label in runtime_labels:
            sim = data_by_runtime_and_task.get(label, {}).get(task_id)
            block = get_cell_block(sim)
            background_color = block["background_color"]
            reward = escape(block["reward"])
            duration = escape(block["duration"])
            db_match = escape(block["db_match"])
            successful_actions_string = escape(block["successful_actions_string"])
            termination_reason = escape(block["termination_reason"])

            # Build actions payload (with conversation snippets)
            actions_bundle = _build_actions_payload(sim or {})
            actions_payload = _serialize_actions_for_attr(actions_bundle)

            # Colored wrapper holds both stats and bottom-right link
            cell_html = f"""
              <div class="cell-box" style="background-color:{background_color}">
                <table class="subtable">
                  <tr class="field"><td>Reward</td><td class="mono">{reward}</td></tr>
                  <tr class="field"><td>Duration</td><td class="mono">{duration}</td></tr>
                  <tr class="field"><td>DB Match</td><td class="mono">{db_match}</td></tr>
                  <tr class="field"><td>Successful Actions</td><td class="mono">{successful_actions_string}</td></tr>
                  <tr class="field"><td>Termination Reason</td><td class="mono">{termination_reason}</td></tr>
                </table>
                <span class="link show-actions"
                      data-runtime="{escape(label)}"
                      data-task="{escape(str(task_id))}"
                      data-actions='{escape(actions_payload)}'>Details</span>
              </div>
            """
            row_cells.append(f"<td>{cell_html}</td>")
        body_rows.append("<tr>" + "".join(row_cells) + "</tr>")

    # Modal + JS (extended to add “Conversation” link per action and second modal)
    modal = """
    <div id="modal-backdrop" class="modal-backdrop" role="dialog" aria-modal="true" aria-hidden="true">
      <div class="modal" role="document">
        <div class="modal-header">
          <div class="modal-title" id="modal-title">Actions</div>
          <button id="modal-close" class="modal-close" aria-label="Close">&times;</button>
        </div>
        <div class="modal-body">
          <div id="modal-content" class="mono">Loading…</div>
        </div>
      </div>
    </div>

    <!-- Second modal for per-action conversation -->
    <div id="modal-backdrop-2" class="modal-backdrop" role="dialog" aria-modal="true" aria-hidden="true">
      <div class="modal" role="document">
        <div class="modal-header">
          <div class="modal-title" id="modal-title-2">Conversation</div>
          <button id="modal-close-2" class="modal-close" aria-label="Close">&times;</button>
        </div>
        <div class="modal-body">
          <div id="modal-content-2" class="mono">Loading…</div>
        </div>
      </div>
    </div>

    <script>
      (function() {
        const backdrop = document.getElementById('modal-backdrop');
        const content = document.getElementById('modal-content');
        const titleEl = document.getElementById('modal-title');
        const closeBtn = document.getElementById('modal-close');

        const backdrop2 = document.getElementById('modal-backdrop-2');
        const content2 = document.getElementById('modal-content-2');
        const titleEl2 = document.getElementById('modal-title-2');
        const closeBtn2 = document.getElementById('modal-close-2');

        function close() {
          backdrop.style.display = 'none';
          backdrop.setAttribute('aria-hidden', 'true');
          content.innerHTML = '';
        }
        function close2() {
          backdrop2.style.display = 'none';
          backdrop2.setAttribute('aria-hidden', 'true');
          content2.innerHTML = '';
        }

        function openWith(runtime, task, actions) {
          titleEl.textContent = `Actions — ${runtime} — Task ${task}`;
          let html = '';
          if (!actions || !actions.length) {
            html = '<div class="muted">No action checks available.</div>';
          } else {
            html += '<table class="actions-table">';
            html += '<thead><tr><th>Name</th><th>action_reward</th><th>action_match</th><th>Conversation</th></tr></thead><tbody>';
            for (let i = 0; i < actions.length; i++) {
              const a = actions[i];
              const reward = (a.action_reward === undefined || a.action_reward === null) ? 'n/a' : a.action_reward;
              const match = (a.action_match === undefined || a.action_match === null) ? 'n/a' : a.action_match;
              const cls = (reward > 0 && match === true) ? 'ok' : (reward > 0 || match === true) ? 'ok' : 'bad';
              const convPayload = JSON.stringify(a.conversation || []);
              html += `<tr>
                        <td>${escapeHtml(String(a.name ?? 'n/a'))}</td>
                        <td class="${cls}">${escapeHtml(String(reward))}</td>
                        <td class="${cls}">${escapeHtml(String(match))}</td>
                        <td><a href="#" class="show-conv" data-action="${escapeHtml(String(a.name ?? 'n/a'))}" data-conv='${escapeHtml(convPayload)}'>View</a></td>
                       </tr>`;
            }
            html += '</tbody></table>';
          }
          content.innerHTML = html;
          // attach handlers for conversation links inside the modal
          content.querySelectorAll('.show-conv').forEach(el => {
            el.addEventListener('click', (ev) => {
              ev.preventDefault();
              const actionName = el.getAttribute('data-action') || 'Action';
              let conv = el.getAttribute('data-conv') || '[]';
              try { conv = JSON.parse(conv); } catch(e) { conv = []; }
              openConversation(actionName, conv);
            });
          });

          backdrop.style.display = 'flex';
          backdrop.setAttribute('aria-hidden', 'false');
        }

        function openConversation(actionName, conv) {
          titleEl2.textContent = `Conversation — ${actionName}`;
          if (!conv || !conv.length) {
            content2.innerHTML = '<div class="muted">No conversation available for this action.</div>';
          } else {
            let html = '';
            for (const m of conv) {
              const role = escapeHtml(String(m.role ?? ''));
              const text = escapeHtml(String(m.content ?? ''));
              html += `<div class="conv-msg"><span class="conv-role">${role}:</span> ${text}</div>`;
            }
            content2.innerHTML = html;
          }
          backdrop2.style.display = 'flex';
          backdrop2.setAttribute('aria-hidden', 'false');
        }

        function attach() {
          document.querySelectorAll('.show-actions').forEach(el => {
            el.addEventListener('click', () => {
              const runtime = el.getAttribute('data-runtime') || 'Runtime';
              const task = el.getAttribute('data-task') || 'n/a';
              let payload = el.getAttribute('data-actions') || '[]';
              try { payload = JSON.parse(payload); } catch(e) { payload = []; }
              openWith(runtime, task, payload);
            });
          });
        }

        function escapeHtml(s) {
          return s.replaceAll('&','&amp;')
                  .replaceAll('<','&lt;')
                  .replaceAll('>','&gt;')
                  .replaceAll('"','&quot;')
                  .replaceAll("'",'&#39;');
        }

        closeBtn.addEventListener('click', close);
        document.getElementById('modal-backdrop').addEventListener('click', (e) => { if (e.target === e.currentTarget) close(); });
        window.addEventListener('keydown', (e) => { if (e.key === 'Escape') { close(); close2(); } });

        closeBtn2.addEventListener('click', close2);
        document.getElementById('modal-backdrop-2').addEventListener('click', (e) => { if (e.target === e.currentTarget) close2(); });

        document.addEventListener('DOMContentLoaded', attach);
      })();
    </script>
    """

    table_html = f"""
    <div class="title">Tau2Bench</div>
    <table style="border: 2px solid">
      {header_html}
      {"".join(body_rows)}
    </table>
    {modal}
    """
    return f"<!DOCTYPE html><html><head><meta charset='utf-8'>{styles}</head><body>{table_html}</body></html>"


def generate_report():
    args = parse_args()
    runtime_labels = []
    datasets = {}
    for inp in args.inputs:
        if ":" not in inp:
            print('Each input must be "path:Label"', file=sys.stderr)
            sys.exit(2)
        path, label = inp.split(":", 1)
        path = path.strip().strip('"').strip("'")
        label = label.strip().strip('"').strip("'")
        runtime_labels.append(label)
        datasets[label] = load_results(path)

    data_by_runtime_and_task = {}
    all_task_ids = set()
    for label, ds in datasets.items():
        sims = ds.get("simulations", []) or []
        by_task = {}
        for sim in sims:
            task_id = sim.get("task_id")
            if task_id is None:
                continue
            by_task.setdefault(task_id, []).append(sim)
        chosen = {tid: pick_simulation_for_task(sim_list) for tid, sim_list in by_task.items()}
        data_by_runtime_and_task[label] = chosen
        all_task_ids.update(chosen.keys())

    html = build_html_table(runtime_labels, all_task_ids, data_by_runtime_and_task)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    generate_report()
