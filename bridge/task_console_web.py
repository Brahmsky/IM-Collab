from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any, Callable

from bridge.task_control import append_control_command
from bridge.task_index import build_task_index, summarize_events
from bridge.task_ops import ack_task, retry_golembot_task

RetryFunc = Callable[..., dict[str, Any]]


def render_console_html(tasks_root: Path, event_dir: Path, flash: str = "") -> str:
    tasks = build_task_index(tasks_root)
    events = summarize_events(event_dir)
    rows = "\n".join(_task_card(task) for task in tasks) or _empty_state()
    flash_html = f'<p class="flash-banner">{escape(flash)}</p>' if flash else ""

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Agent-Pilot 多端协同办公助手</title>
  <style>
    /* ── Design Tokens ── */
    :root {{
      --primary: #3370FF;
      --primary-hover: #2B5FD9;
      --primary-soft: #DEEBFF;
      --primary-ring: rgba(51, 112, 255, 0.25);
      --success: #34C724;
      --success-soft: #E8F9E8;
      --warning: #F7B329;
      --warning-soft: #FFF8E6;
      --warning-border: #FFE08A;
      --danger: #F54A45;
      --danger-hover: #D93B3B;
      --danger-soft: #FEE8E7;
      --purple: #9B51E0;
      --purple-soft: #F3E8FC;

      --bg: #F5F6F7;
      --surface: #FFFFFF;
      --surface-hover: #F9FAFB;
      --text: #1F2329;
      --text-secondary: #646A73;
      --text-tertiary: #8F959E;
      --border: #DEE0E3;
      --border-light: #EBECEE;

      --shadow-xs: 0 1px 2px rgba(0, 0, 0, 0.04);
      --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04);
      --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.06), 0 2px 4px rgba(0, 0, 0, 0.04);
      --shadow-lg: 0 12px 32px rgba(0, 0, 0, 0.08), 0 4px 8px rgba(0, 0, 0, 0.04);

      --radius-sm: 6px;
      --radius-md: 10px;
      --radius-lg: 14px;
      --radius-xl: 20px;

      --transition: 150ms cubic-bezier(0.4, 0, 0.2, 1);
      --transition-slow: 250ms cubic-bezier(0.4, 0, 0.2, 1);
    }}

    /* ── Reset ── */
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.6;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
    }}

    /* ── Layout ── */
    .app-shell {{
      display: flex;
      flex-direction: column;
      min-height: 100vh;
    }}

    .topnav {{
      position: sticky;
      top: 0;
      z-index: 40;
      display: flex;
      align-items: center;
      justify-content: space-between;
      height: 52px;
      padding: 0 28px;
      background: var(--surface);
      border-bottom: 1px solid var(--border);
      box-shadow: var(--shadow-xs);
    }}

    .topnav-brand {{
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 15px;
      font-weight: 700;
      color: var(--text);
      letter-spacing: -0.01em;
      text-decoration: none;
    }}

    .topnav-logo {{
      width: 26px;
      height: 26px;
      color: #F76956;
      flex-shrink: 0;
    }}

    .topnav-right {{
      display: flex;
      align-items: center;
      gap: 18px;
    }}

    .topnav-link {{
      font-size: 13px;
      font-weight: 500;
      color: var(--text-secondary);
      text-decoration: none;
      transition: color var(--transition);
    }}

    .topnav-link:hover {{ color: var(--primary); }}

    .topnav-avatar {{
      width: 30px;
      height: 30px;
      border-radius: 999px;
      border: 1.5px solid var(--border);
      background: linear-gradient(135deg, #3370FF 0%, #9B51E0 100%);
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-size: 12px;
      font-weight: 700;
      flex-shrink: 0;
    }}

    /* ── Main Content ── */
    .main-content {{
      max-width: 1280px;
      width: 100%;
      margin: 0 auto;
      padding: 28px 28px 56px;
    }}

    .flash-banner {{
      background: var(--success-soft);
      border: 1px solid #86EFAC;
      color: #166534;
      padding: 10px 16px;
      border-radius: var(--radius-md);
      font-size: 13px;
      font-weight: 500;
      margin-bottom: 20px;
      animation: slideDown var(--transition-slow);
    }}

    @keyframes slideDown {{
      from {{ opacity: 0; transform: translateY(-8px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}

    /* ── Hero Header ── */
    .hero {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 24px;
      margin-bottom: 24px;
    }}

    .hero-title-section {{ flex: 1; min-width: 0; }}

    .hero-eyebrow {{
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--primary);
      margin-bottom: 4px;
    }}

    .hero-title {{
      font-size: 30px;
      font-weight: 800;
      letter-spacing: -0.03em;
      color: var(--text);
      line-height: 1.2;
    }}

    .hero-subtitle {{
      margin-top: 6px;
      font-size: 14px;
      color: var(--text-secondary);
    }}

    /* ── Stats Row ── */
    .stats-row {{
      display: flex;
      gap: 16px;
      margin-bottom: 24px;
    }}

    .stat-card {{
      flex: 1;
      min-width: 140px;
      display: flex;
      align-items: center;
      gap: 14px;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      padding: 18px 22px;
      box-shadow: var(--shadow-sm);
      transition: box-shadow var(--transition), border-color var(--transition);
    }}

    .stat-card:hover {{
      box-shadow: var(--shadow-md);
      border-color: var(--primary-soft);
    }}

    .stat-icon {{
      width: 42px;
      height: 42px;
      border-radius: var(--radius-md);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      flex-shrink: 0;
    }}

    .stat-icon.events {{ background: var(--primary-soft); color: var(--primary); }}
    .stat-icon.tasks {{ background: #FFF1F0; color: #F76956; }}

    .stat-label {{
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--text-tertiary);
      margin-bottom: 2px;
    }}

    .stat-value {{
      font-size: 28px;
      font-weight: 800;
      letter-spacing: -0.02em;
      color: var(--text);
      line-height: 1;
    }}

    /* ── Task Card ── */
    .task {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-xl);
      padding: 26px 28px 28px;
      margin-bottom: 24px;
      box-shadow: var(--shadow-sm);
      transition: box-shadow var(--transition);
    }}

    .task:hover {{ box-shadow: var(--shadow-md); }}

    .task-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 20px;
      margin-bottom: 22px;
      flex-wrap: wrap;
    }}

    .task-title-group {{ flex: 1; min-width: 200px; }}

    .task-id {{
      font-size: 16px;
      font-weight: 700;
      letter-spacing: -0.01em;
      color: var(--text);
      word-break: break-all;
    }}

    .task-meta {{
      font-size: 12px;
      color: var(--text-tertiary);
      margin-top: 3px;
    }}

    .task-status-group {{
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 6px;
    }}

    /* ── State Badges ── */
    .state {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      font-weight: 700;
      padding: 5px 12px;
      border-radius: 999px;
      white-space: nowrap;
    }}

    .state::before {{
      content: "";
      width: 7px;
      height: 7px;
      border-radius: 999px;
      flex-shrink: 0;
    }}

    .state-queued       {{ background: #F2F3F5; color: #646A73; }} .state-queued::before       {{ background: #C7CAD1; }}
    .state-running      {{ background: var(--primary-soft); color: var(--primary); }} .state-running::before      {{ background: var(--primary); animation: pulse-dot 1.5s infinite; }}
    .state-waiting_for_user {{ background: var(--warning-soft); color: #B37600; }} .state-waiting_for_user::before {{ background: var(--warning); animation: pulse-dot 1.5s infinite; }}
    .state-completed    {{ background: var(--success-soft); color: #166534; }} .state-completed::before    {{ background: var(--success); }}
    .state-failed       {{ background: var(--danger-soft); color: #991B1B; }} .state-failed::before       {{ background: var(--danger); }}

    @keyframes pulse-dot {{
      0%, 100% {{ opacity: 1; }}
      50% {{ opacity: 0.4; }}
    }}

    /* ── 3-Column Grid ── */
    .task-grid {{
      display: grid;
      grid-template-columns: 1.2fr 1fr 1fr;
      gap: 16px;
      margin-bottom: 22px;
    }}

    /* ── Panels ── */
    .panel {{
      background: var(--surface);
      border: 1px solid var(--border-light);
      border-radius: var(--radius-lg);
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }}

    .panel-header {{
      display: flex;
      align-items: center;
      gap: 8px;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--border-light);
    }}

    .panel-header-icon {{
      width: 26px;
      height: 26px;
      border-radius: var(--radius-sm);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 15px;
      font-weight: 700;
      flex-shrink: 0;
    }}

    .panel-header-icon.col1 {{ background: var(--primary-soft); color: var(--primary); }}
    .panel-header-icon.col2 {{ background: var(--purple-soft); color: var(--purple); }}
    .panel-header-icon.col3 {{ background: var(--success-soft); color: #166534; }}

    .panel-title {{
      font-size: 14px;
      font-weight: 700;
      letter-spacing: -0.01em;
    }}

    /* ── Chat Bubbles ── */
    .chat-list {{
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}

    .chat-row {{
      display: flex;
      gap: 8px;
      align-items: flex-start;
    }}

    .chat-row.user {{ flex-direction: row-reverse; }}

    .chat-avatar {{
      width: 28px;
      height: 28px;
      border-radius: 999px;
      flex-shrink: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
      font-weight: 700;
      color: white;
      margin-top: 2px;
    }}

    .chat-avatar.user {{ background: linear-gradient(135deg, #F76956, #F54A45); }}
    .chat-avatar.agent {{ background: linear-gradient(135deg, #3370FF, #9B51E0); }}

    .chat-bubble {{
      max-width: 85%;
      padding: 10px 14px;
      border-radius: var(--radius-lg);
      font-size: 13px;
      line-height: 1.6;
      white-space: pre-wrap;
      word-break: break-word;
    }}

    .chat-bubble.user {{
      background: var(--primary);
      color: #FFFFFF;
      border-bottom-right-radius: var(--radius-sm);
    }}

    .chat-bubble.agent {{
      background: #F2F3F5;
      color: var(--text);
      border-bottom-left-radius: var(--radius-sm);
    }}

    /* ── Confirm Banner ── */
    .confirm-banner {{
      margin-top: 4px;
      padding: 12px 14px;
      border-radius: var(--radius-md);
      background: var(--warning-soft);
      border: 1px solid var(--warning-border);
      display: flex;
      align-items: flex-start;
      gap: 8px;
      font-size: 12px;
      color: #B37600;
      line-height: 1.5;
    }}

    .confirm-banner-icon {{
      font-size: 16px;
      flex-shrink: 0;
      margin-top: 1px;
    }}

    /* ── Tag Cloud ── */
    .tag-section {{
      display: flex;
      flex-direction: column;
      gap: 10px;
    }}

    .tag-section-label {{
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--text-tertiary);
    }}

    .tag-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }}

    .tag {{
      display: inline-flex;
      align-items: center;
      padding: 5px 10px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 600;
      background: #F2F3F5;
      color: var(--text-secondary);
      border: 1px solid var(--border-light);
    }}

    .tag.artifact-doc {{ background: #DEEBFF; color: var(--primary); border-color: transparent; }}
    .tag.artifact-slides {{ background: #FFF1F0; color: #F76956; border-color: transparent; }}
    .tag.artifact-whiteboard {{ background: #F3E8FC; color: var(--purple); border-color: transparent; }}

    /* ── Codex Status ── */
    .codex-card {{
      margin-top: 4px;
      padding: 14px 16px;
      background: #F9FAFB;
      border: 1px solid var(--border-light);
      border-radius: var(--radius-md);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}

    .codex-card-label {{
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--text-tertiary);
      margin-bottom: 3px;
    }}

    .codex-card-value {{
      font-size: 13px;
      font-weight: 600;
      color: var(--text);
    }}

    .codex-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 700;
      background: var(--primary-soft);
      color: var(--primary);
    }}

    .codex-badge::before {{
      content: "";
      width: 6px;
      height: 6px;
      border-radius: 999px;
      background: var(--primary);
      animation: pulse-dot 1.5s infinite;
    }}

    /* ── Timeline ── */
    .timeline {{
      list-style: none;
      position: relative;
      padding-left: 22px;
    }}

    .timeline::before {{
      content: "";
      position: absolute;
      left: 7px;
      top: 4px;
      bottom: 4px;
      width: 1.5px;
      background: var(--border);
    }}

    .timeline li {{
      position: relative;
      padding: 0 0 18px 18px;
      font-size: 13px;
      color: var(--text-tertiary);
      transition: color var(--transition);
    }}

    .timeline li:last-child {{ padding-bottom: 0; }}

    .timeline li::before {{
      content: "";
      position: absolute;
      left: -16px;
      top: 3px;
      width: 14px;
      height: 14px;
      border-radius: 999px;
      background: var(--surface);
      border: 2px solid var(--border);
      z-index: 1;
      transition: all var(--transition);
    }}

    .timeline li.done {{
      color: var(--text);
      font-weight: 600;
    }}

    .timeline li.done::before {{
      background: var(--success);
      border-color: var(--success);
    }}

    .timeline li.active {{
      color: var(--primary);
      font-weight: 700;
    }}

    .timeline li.active::before {{
      background: var(--primary);
      border-color: var(--primary);
      box-shadow: 0 0 0 5px var(--primary-ring);
    }}

    .timeline li.failed {{
      color: var(--danger);
      font-weight: 700;
    }}

    .timeline li.failed::before {{
      background: var(--danger);
      border-color: var(--danger);
    }}

    .timeline-step-label {{
      display: block;
      font-size: 13px;
    }}

    .timeline-step-time {{
      display: block;
      font-size: 11px;
      margin-top: 1px;
      opacity: 0.7;
    }}

    /* ── Progress Summary ── */
    .progress-summary {{
      margin-top: 8px;
      font-size: 12px;
      color: var(--text-secondary);
      line-height: 1.5;
    }}

    /* ── Footer Grid ── */
    .task-footer {{
      display: grid;
      grid-template-columns: 1.4fr 0.6fr;
      gap: 16px;
    }}

    /* ── Artifacts ── */
    .artifact-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
      gap: 10px;
      margin-top: 4px;
    }}

    .artifact {{
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
      padding: 20px 14px;
      border-radius: var(--radius-md);
      text-align: center;
      text-decoration: none;
      transition: all var(--transition);
      border: 1.5px dashed var(--border);
      background: var(--surface-hover);
      color: var(--text-tertiary);
      cursor: default;
    }}

    .artifact.ready {{
      border-style: solid;
      border-color: var(--primary-soft);
      background: #F5F8FF;
      color: var(--text);
      cursor: pointer;
      box-shadow: var(--shadow-xs);
    }}

    .artifact.ready:hover {{
      border-color: var(--primary);
      background: var(--primary-soft);
      box-shadow: var(--shadow-sm);
      transform: translateY(-1px);
    }}

    .artifact-icon {{
      font-size: 28px;
      transition: transform var(--transition);
    }}

    .artifact.ready:hover .artifact-icon {{
      transform: scale(1.1);
    }}

    .artifact-title {{
      font-size: 13px;
      font-weight: 700;
      color: var(--text);
    }}

    .artifact-status {{
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }}

    .artifact-status.done {{ color: var(--success); }}
    .artifact-status.progress {{ color: var(--primary); }}
    .artifact-status.waiting {{ color: var(--text-tertiary); }}

    /* ── Actions ── */
    .task-actions {{
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}

    .btn-group {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}

    .btn {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 8px 16px;
      border-radius: var(--radius-md);
      font-size: 13px;
      font-weight: 600;
      border: 1px solid transparent;
      cursor: pointer;
      transition: all var(--transition);
      white-space: nowrap;
      text-decoration: none;
      font-family: inherit;
    }}

    .btn:focus-visible {{
      outline: 2px solid var(--primary);
      outline-offset: 2px;
    }}

    .btn-primary {{
      background: var(--primary);
      color: #FFFFFF;
      border-color: var(--primary);
    }}

    .btn-primary:hover {{ background: var(--primary-hover); border-color: var(--primary-hover); }}
    .btn-primary:active {{ transform: scale(0.97); }}

    .btn-danger {{
      background: var(--danger);
      color: #FFFFFF;
      border-color: var(--danger);
    }}

    .btn-danger:hover {{ background: var(--danger-hover); border-color: var(--danger-hover); }}
    .btn-danger:active {{ transform: scale(0.97); }}

    .btn-outline {{
      background: var(--surface);
      color: var(--text);
      border-color: var(--border);
    }}

    .btn-outline:hover {{ background: var(--surface-hover); border-color: var(--text-tertiary); }}

    .btn-ghost {{
      background: transparent;
      color: var(--text-secondary);
      border-color: transparent;
    }}

    .btn-ghost:hover {{ background: var(--surface-hover); color: var(--text); }}

    .btn-icon {{
      width: 16px;
      height: 16px;
      flex-shrink: 0;
    }}

    /* ── Form Elements ── */
    .input-row {{
      display: flex;
      gap: 8px;
      margin-top: 4px;
    }}

    .input {{
      flex: 1;
      min-width: 0;
      padding: 9px 12px;
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      font-size: 13px;
      font-family: inherit;
      background: var(--surface);
      color: var(--text);
      transition: border-color var(--transition), box-shadow var(--transition);
    }}

    .input::placeholder {{ color: var(--text-tertiary); }}
    .input:focus {{ outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px var(--primary-ring); }}

    .select {{
      padding: 8px 28px 8px 10px;
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      font-size: 12px;
      font-family: inherit;
      background: var(--surface);
      color: var(--text);
      cursor: pointer;
      appearance: none;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%238F959E' stroke-width='2'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E");
      background-repeat: no-repeat;
      background-position: right 8px center;
      transition: border-color var(--transition);
    }}

    .select:focus {{ outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px var(--primary-ring); }}

    .checkbox-row {{
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      color: var(--text);
      cursor: pointer;
    }}

    .checkbox {{
      width: 15px;
      height: 15px;
      accent-color: var(--primary);
      cursor: pointer;
    }}

    /* ── Divider ── */
    .divider {{
      border: none;
      border-top: 1px solid var(--border-light);
      margin: 4px 0;
    }}

    /* ── Config Row ── */
    .config-row {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 16px;
    }}

    .config-field {{
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}

    .config-label {{
      font-size: 11px;
      font-weight: 600;
      color: var(--text-secondary);
    }}

    /* ── Error ── */
    .error-box {{
      background: var(--danger-soft);
      border: 1px solid #FECACA;
      color: #991B1B;
      padding: 10px 14px;
      border-radius: var(--radius-md);
      font-size: 12px;
      font-weight: 500;
      margin-top: 8px;
    }}

    /* ── Empty State ── */
    .empty {{
      background: var(--surface);
      border: 2px dashed var(--border);
      border-radius: var(--radius-xl);
      padding: 52px 32px;
      text-align: center;
      color: var(--text-tertiary);
    }}

    .empty-icon {{
      font-size: 44px;
      margin-bottom: 14px;
      display: block;
      opacity: 0.5;
    }}

    .empty-title {{
      font-size: 17px;
      font-weight: 700;
      color: var(--text-secondary);
      margin-bottom: 6px;
    }}

    .empty-desc {{
      font-size: 13px;
      line-height: 1.5;
    }}

    /* ── Responsive ── */
    @media (max-width: 1200px) {{
      .task-grid {{ grid-template-columns: 1fr 1fr; }}
      .task-grid .panel:first-child {{ grid-column: 1 / -1; }}
      .task-footer {{ grid-template-columns: 1fr; }}
    }}

    @media (max-width: 800px) {{
      .task-grid {{ grid-template-columns: 1fr; }}
      .task-footer {{ grid-template-columns: 1fr; }}
      .hero {{ flex-direction: column; }}
      .stats-row {{ flex-direction: column; }}
      .main-content {{ padding: 16px 14px 40px; }}
      .topnav {{ padding: 0 14px; }}
      .task {{ padding: 18px 16px 20px; }}
      .btn-group {{ flex-direction: column; }}
      .btn-group .btn {{ justify-content: center; }}
    }}
  </style>
</head>
<body>
<div class="app-shell">

  <!-- Top Navigation -->
  <nav class="topnav">
    <a class="topnav-brand" href="/">
      <svg class="topnav-logo" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <path d="M36.7273 44C33.9891 44 31.6043 39.8386 30.3636 33.69C29.123 39.8386 26.7382 44 24 44C21.2618 44 18.877 39.8386 17.6364 33.69C16.3957 39.8386 14.0109 44 11.2727 44C7.25611 44 4 35.0457 4 24C4 12.9543 7.25611 4 11.2727 4C14.0109 4 16.3957 8.16144 17.6364 14.31C18.877 8.16144 21.2618 4 24 4C26.7382 4 29.123 8.16144 30.3636 14.31C31.6043 8.16144 33.9891 4 36.7273 4C40.7439 4 44 12.9543 44 24C44 35.0457 40.7439 44 36.7273 44Z" fill="currentColor"/>
      </svg>
      AGENT-PILOT 办公助手
    </a>
    <div class="topnav-right">
      <span class="topnav-link">多端协同办公工作台</span>
      <div class="topnav-avatar" aria-label="当前用户">Y</div>
    </div>
  </nav>

  <div class="main-content">

    {flash_html}

    <!-- Hero -->
    <section class="hero">
      <div class="hero-title-section">
        <p class="hero-eyebrow">Agent-Pilot 办公助手</p>
        <h1 class="hero-title">多端协同办公工作台</h1>
        <p class="hero-subtitle">用自然语言驱动 Agent，展示理解、执行与交付。</p>
      </div>
    </section>

    <!-- Stats Row -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-icon events">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        </div>
        <div>
          <p class="stat-label">IM 事件</p>
          <p class="stat-value">{events.total}</p>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon tasks">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
        </div>
        <div>
          <p class="stat-label">待办任务</p>
          <p class="stat-value">{len(tasks)}</p>
        </div>
      </div>
    </div>

    {rows}

  </div>
</div>
</body>
</html>"""


def handle_console_action(
    tasks_root: Path,
    form: dict[str, str],
    retry: RetryFunc = retry_golembot_task,
) -> str:
    action = form.get("action", "")
    task_id = _required(form, "task_id")
    task_dir = tasks_root / task_id

    if action == "append":
        append_control_command(
            task_dir,
            "append_instruction",
            {"text": _required(form, "text")},
            operator="operator",
        )
        return f"已为任务 {task_id} 追加指令"

    if action == "interrupt":
        append_control_command(task_dir, "interrupt", {}, operator="operator")
        return f"已向任务 {task_id} 发送打断指令"

    if action == "ack":
        ack_task(task_dir, operator="operator", note=form.get("note", ""))
        return f"已确认任务 {task_id}"

    if action == "retry":
        retry(
            task_dir,
            generator=form.get("generator") or "local",
            publish=form.get("publish") in {"1", "true", "on"},
        )
        return f"已重新启动任务 {task_id}"

    raise ValueError(f"unsupported action: {action}")


# ── Task Card ────────────────────────────────────────────────────────────────

def _task_card(task: Any) -> str:
    error_html = f'<div class="error-box">错误：{escape(task.error)}</div>' if task.error else ""
    document = getattr(task, "document_url", "") or ""
    slides = getattr(task, "slides_url", "") or ""
    whiteboard = getattr(task, "whiteboard_token", "") or ""
    summary_text = escape(task.summary or "Agent 正在把群聊内容转为可交付的方案文档、演示稿与白板流程图。")
    state_label = _state_label(task.state)
    state_class = task.state

    return f"""<section class="task">
  <div class="task-header">
    <div class="task-title-group">
      <h2 class="task-id">{escape(task.task_id)}</h2>
      <p class="task-meta">最后更新：{escape(task.updated_at or "-")}</p>
    </div>
    <div class="task-status-group">
      <span class="state state-{state_class}">{state_label}</span>
      <span style="font-size:11px;color:var(--text-tertiary)">会话：{escape(task.session_key or "本地演示")}</span>
    </div>
  </div>

  <div class="task-grid">

    <!-- Column 1: Natural Language Input -->
    <div class="panel">
      <div class="panel-header">
        <span class="panel-header-icon col1">1</span>
        <span class="panel-title">自然语言输入</span>
      </div>
      <div class="chat-list">
        <div class="chat-row user">
          <span class="chat-avatar user">U</span>
          <div class="chat-bubble user">{summary_text}</div>
        </div>
        <div class="chat-row agent">
          <span class="chat-avatar agent">AI</span>
          <div class="chat-bubble agent">Agent 已接收，请确认理解、进度与交付内容。</div>
        </div>
      </div>
      {_append_form(task.task_id)}
      {_confirmation_banner(task)}
    </div>

    <!-- Column 2: Agent Understanding -->
    <div class="panel">
      <div class="panel-header">
        <span class="panel-header-icon col2">2</span>
        <span class="panel-title">Agent 理解</span>
      </div>
      <div class="tag-section">
        <span class="tag-section-label">核心目标</span>
        <div class="tag-row">
          <span class="tag">生成答辩材料</span>
          <span class="tag">方案文档</span>
          <span class="tag">演示文稿</span>
        </div>
      </div>
      <div class="tag-section">
        <span class="tag-section-label">产出类型</span>
        <div class="tag-row">
          <span class="tag artifact-doc">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:2px"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            文档
          </span>
          <span class="tag artifact-slides">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:2px"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
            演示文稿
          </span>
          <span class="tag artifact-whiteboard">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:2px"><circle cx="12" cy="12" r="3"/><path d="M12 2v4m0 12v4M2 12h4m12 0h4"/></svg>
            白板
          </span>
        </div>
      </div>
      <div class="codex-card">
        <div>
          <div class="codex-card-label">CODEX 状态</div>
          <div class="codex-card-value">知识同步中</div>
        </div>
        <span class="codex-badge">运行中</span>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:11px;color:var(--text-tertiary);margin-top:4px;">
        <div><span style="display:block;font-weight:600;color:var(--text-secondary);margin-bottom:1px;">最新操作</span>{escape(task.last_control_type or "无")}</div>
        <div><span style="display:block;font-weight:600;color:var(--text-secondary);margin-bottom:1px;">控制次数</span>{task.control_count}</div>
        <div><span style="display:block;font-weight:600;color:var(--text-secondary);margin-bottom:1px;">Codex 线程</span>{escape(task.codex_thread_id or "-")}</div>
        <div><span style="display:block;font-weight:600;color:var(--text-secondary);margin-bottom:1px;">活跃回合</span>{escape(task.active_turn_id or "-")}</div>
      </div>
    </div>

    <!-- Column 3: Execution Progress -->
    <div class="panel">
      <div class="panel-header">
        <span class="panel-header-icon col3">3</span>
        <span class="panel-title">执行进度</span>
      </div>
      <ol class="timeline">
        <li class="{_step_class(task, "intent")}">
          <span class="timeline-step-label">理解 IM 意图</span>
        </li>
        <li class="{_step_class(task, "brief")}">
          <span class="timeline-step-label">生成群聊 brief</span>
        </li>
        <li class="{_step_class(task, "doc")}">
          <span class="timeline-step-label">生成方案文档</span>
        </li>
        <li class="{_step_class(task, "slides")}">
          <span class="timeline-step-label">生成答辩 PPT</span>
        </li>
        <li class="{_step_class(task, "whiteboard")}">
          <span class="timeline-step-label">生成白板流程图</span>
        </li>
        <li class="{_step_class(task, "delivery")}">
          <span class="timeline-step-label">汇总交付</span>
        </li>
      </ol>
      <div class="progress-summary">{escape(task.summary or "正在生成中...")}</div>
    </div>

  </div>

  <!-- Footer: Artifacts + Operations -->
  <div class="task-footer">
    <div class="panel">
      <div class="panel-header">
        <span style="font-weight:700;font-size:13px;letter-spacing:-.01em;">交付产物</span>
      </div>
      <div class="artifact-grid">
        {_artifact_card("方案文档", document, "等待生成", "doc")}
        {_artifact_card("演示文稿 PPT", slides, "等待生成", "slides")}
        {_artifact_card("白板流程图", whiteboard, "等待生成", "whiteboard")}
      </div>
      {error_html}
    </div>

    <div class="panel">
      <div class="panel-header">
        <span style="font-weight:700;font-size:13px;letter-spacing:-.01em;">人工接管 / 操作</span>
      </div>
      {_interrupt_ack_retry_form(task.task_id)}
    </div>
  </div>
</section>"""


# ── Helpers ──────────────────────────────────────────────────────────────────

def _append_form(task_id: str) -> str:
    return f"""<form method="post" class="input-row" style="margin-top:10px;">
    <input type="hidden" name="action" value="append">
    <input type="hidden" name="task_id" value="{escape(task_id)}">
    <input class="input" name="text" placeholder="继续修改：把 PPT 改成更正式、适合比赛答辩" required>
    <button class="btn btn-primary" type="submit">发送</button>
  </form>"""


def _confirmation_banner(task: Any) -> str:
    if getattr(task, "state", "") != "waiting_for_user":
        return ""
    return """<div class="confirm-banner">
    <span class="confirm-banner-icon">&#9888;</span>
    <span>Agent 正在等待您的确认。请在操作面板中确认或追加指令以继续。</span>
  </div>"""


def _interrupt_ack_retry_form(task_id: str) -> str:
    t = escape(task_id)
    return f"""<form method="post" style="display:flex;flex-direction:column;gap:10px;">
    <input type="hidden" name="task_id" value="{t}">

    <div class="btn-group">
      <button class="btn btn-danger" name="action" value="interrupt" type="submit">
        <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="6" width="12" height="12" rx="1"/></svg>
        打断任务
      </button>
      <button class="btn btn-outline" name="action" value="ack" type="submit">
        <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
        确认
      </button>
    </div>

    <hr class="divider">

    <div class="config-row">
      <div class="config-field">
        <label class="config-label">生成引擎</label>
        <select class="select" name="generator">
          <option value="local">local 本地演示</option>
          <option value="app-server">app-server</option>
          <option value="codex">codex</option>
        </select>
      </div>
      <label class="checkbox-row" style="margin-top:18px;">
        <input class="checkbox" type="checkbox" name="publish" value="1">
        同步发布至飞书
      </label>
    </div>

    <div class="input-row" style="margin-top:2px;">
      <input class="input" name="note" placeholder="确认备注（可选）">
      <button class="btn btn-primary" name="action" value="retry" type="submit">重试任务</button>
    </div>
  </form>"""


def _state_label(state: str) -> str:
    labels = {
        "queued": "排队中",
        "running": "运行中",
        "waiting_for_user": "等待用户确认",
        "completed": "已完成",
        "failed": "失败",
    }
    return labels.get(state, state)


def _step_class(task: Any, step: str) -> str:
    state = task.state

    if state == "failed":
        return "failed"

    if step == "intent":
        return "done"

    if step == "brief":
        return "done" if state in {"running", "waiting_for_user", "completed"} else ""

    if step == "doc":
        return "done" if task.document_url or state == "completed" else ("active" if state == "running" else "")

    if step == "slides":
        return "done" if task.slides_url or state == "completed" else ("active" if state == "running" else "")

    if step == "whiteboard":
        return "done" if task.whiteboard_token or state == "completed" else ("active" if state == "running" else "")

    if step == "delivery":
        return "done" if state == "completed" else ("active" if state == "running" else "")

    return ""


def _artifact_card(title: str, value: str, empty: str, kind: str = "doc") -> str:
    if value:
        safe_value = escape(value)
        if value.startswith("http"):
            return f"""<a class="artifact ready" href="{safe_value}" target="_blank" rel="noopener">
  <span class="artifact-icon">{_artifact_icon(kind)}</span>
  <span class="artifact-title">{escape(title)}</span>
  <span class="artifact-status done">已生成</span>
</a>"""
        return f"""<div class="artifact ready">
  <span class="artifact-icon">{_artifact_icon(kind)}</span>
  <span class="artifact-title">{escape(title)}</span>
  <span class="artifact-status done">{safe_value}</span>
</div>"""

    return f"""<div class="artifact">
  <span class="artifact-icon" style="opacity:0.35">{_artifact_icon(kind)}</span>
  <span class="artifact-title">{escape(title)}</span>
  <span class="artifact-status waiting">{escape(empty)}</span>
</div>"""


def _artifact_icon(kind: str) -> str:
    icons = {
        "doc": '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>',
        "slides": '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>',
        "whiteboard": '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="6" r="2"/><circle cx="6" cy="12" r="2"/><circle cx="18" cy="12" r="2"/><circle cx="12" cy="18" r="2"/><line x1="12" y1="8" x2="12" y2="10"/><line x1="8.5" y1="10.5" x2="10.2" y2="11.2"/><line x1="15.5" y1="10.5" x2="13.8" y2="11.2"/></svg>',
    }
    return icons.get(kind, icons["doc"])


def _empty_state() -> str:
    return """<section class="empty">
  <span class="empty-icon">
    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
  </span>
  <h2 class="empty-title">暂无任务</h2>
  <p class="empty-desc">请先运行本地 demo，或从飞书 IM 触发一个任务。</p>
</section>"""


def _required(form: dict[str, str], key: str) -> str:
    value = form.get(key, "").strip()
    if not value:
        raise ValueError(f"missing field: {key}")
    return value
