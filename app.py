"""
CDDA Meeting Manager — Dash Application.
Deployed on Posit Connect as python-dash.

Entrypoint: app:server
"""

import dash
from dash import html, dcc, Input, Output, State, no_update, ALL
from dash.exceptions import PreventUpdate
import json
import base64
import logging
from datetime import datetime
from flask import request as flask_request

import config
from fabric_graph import get_data_layer, generate_recurring_dates

logger = logging.getLogger(__name__)

# ============================================================================
# Dash App
# ============================================================================

app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True,
    title="CDDA Meeting Manager",
)
server = app.server  # Required for Posit Connect entrypoint app:server

# ============================================================================
# Helper functions
# ============================================================================


def _get_current_user():
    """Get current user email from Posit Connect headers or dev config."""
    # 1. Dev override (only in non-production environments)
    if config.DEV_USER_EMAIL and config.APP_ENVIRONMENT.lower() != "production":
        print(f"[auth] Using DEV_USER_EMAIL: {config.DEV_USER_EMAIL}", flush=True)
        return config.DEV_USER_EMAIL.strip().lower()
    # 2. Posit Connect JWT
    try:
        creds = flask_request.headers.get("RStudio-Connect-Credentials", "")
        if creds and "." in creds:
            payload = creds.split(".")[1]
            payload += "=" * (-len(payload) % 4)
            data = json.loads(base64.urlsafe_b64decode(payload))
            print(f"[auth] JWT payload keys: {list(data.keys())}", flush=True)
            print(f"[auth] JWT data: {data}", flush=True)
            email = data.get("email", data.get("username", ""))
            if email:
                print(f"[auth] Detected user: {email}", flush=True)
                return email.strip().lower()
            else:
                print("[auth] JWT has no 'email' or 'username' key", flush=True)
        else:
            # Log all available headers to find the right one
            print(f"[auth] No RStudio-Connect-Credentials header found", flush=True)
            print(f"[auth] Available headers: {list(flask_request.headers.keys())}", flush=True)
    except Exception as exc:
        print(f"[auth] Error decoding JWT: {exc}", flush=True)
    print(f"[auth] Falling back to 'anonymous'", flush=True)
    print(f"[auth] RLS_ADMINS={config.RLS_ADMINS}", flush=True)
    print(f"[auth] APPROVER_EMAILS={config.APPROVER_EMAILS}", flush=True)
    return "anonymous"


def _is_admin(email):
    return bool(email and email != "anonymous" and email in config.RLS_ADMINS)


def _is_approver(email):
    return bool(email and email != "anonymous" and email in config.APPROVER_EMAILS)


# ============================================================================
# Style tokens
# ============================================================================

HEADER = {
    "background": "linear-gradient(135deg, #0B1D3A, #1E4EBC)",
    "color": "white",
    "padding": "24px 32px",
}

CONTAINER = {
    "maxWidth": "1400px",
    "margin": "24px auto",
    "padding": "0 24px",
}

CARD = {
    "background": "white",
    "borderRadius": "8px",
    "padding": "20px",
    "marginBottom": "16px",
    "boxShadow": "0 1px 3px rgba(0,0,0,0.1)",
    "border": "1px solid #e0e0e0",
}

STATUS_BAR = {
    **CARD,
    "borderLeft": "4px solid #0B1D3A",
    "marginBottom": "24px",
}

BTN = {
    "background": "#0B1D3A",
    "color": "white",
    "border": "none",
    "borderRadius": "6px",
    "padding": "10px 20px",
    "cursor": "pointer",
    "fontSize": "14px",
    "marginRight": "8px",
}

BTN_BACK = {**BTN, "background": "#6c757d"}
BTN_OK = {**BTN, "background": "#198754"}
BTN_DEL = {**BTN, "background": "#dc3545"}

BTN_ARCHIVE = {**BTN, "background": "#d97706"}
BTN_RESTORE = {**BTN, "background": "#7c3aed"}
BTN_MANAGE = {
    "background": "transparent",
    "color": "#1E4EBC",
    "border": "1px solid #1E4EBC",
    "borderRadius": "6px",
    "padding": "6px 14px",
    "cursor": "pointer",
    "fontSize": "12px",
    "fontFamily": "inherit",
}

INPUT = {
    "width": "100%",
    "padding": "10px",
    "border": "1px solid #ccc",
    "borderRadius": "6px",
    "marginBottom": "12px",
    "fontSize": "14px",
}

# Sidebar styles
SIDEBAR = {
    "width": "300px",
    "minWidth": "300px",
    "background": "white",
    "borderRadius": "8px",
    "boxShadow": "0 1px 3px rgba(0,0,0,0.1)",
    "display": "flex",
    "flexDirection": "column",
    "overflow": "hidden",
    "border": "1px solid #e0e0e0",
}

SB_ITEM = {
    "padding": "14px 16px",
    "margin": "4px 8px",
    "borderRadius": "6px",
    "cursor": "pointer",
    "borderLeft": "3px solid transparent",
    "background": "#f9fafb",
    "transition": "all 0.15s",
}

SB_ITEM_ACTIVE = {
    **SB_ITEM,
    "background": "#e8eefb",
    "borderLeftColor": "#1E4EBC",
}

MAIN_PANEL = {
    "flex": "1",
    "background": "white",
    "borderRadius": "8px",
    "boxShadow": "0 1px 3px rgba(0,0,0,0.1)",
    "display": "flex",
    "flexDirection": "column",
    "overflow": "hidden",
    "border": "1px solid #e0e0e0",
}

DOC_CHIP = {
    "display": "inline-flex",
    "alignItems": "center",
    "background": "#f0f4ff",
    "border": "1px solid #d0d8ef",
    "borderRadius": "4px",
    "padding": "4px 10px",
    "fontSize": "12px",
    "color": "#1E4EBC",
    "marginRight": "8px",
    "marginTop": "6px",
}

BADGE_STYLES = {
    "Pending": {"background": "#fef3c7", "color": "#92400e"},
    "Approved": {"background": "#d1fae5", "color": "#065f46"},
    "Rejected": {"background": "#fee2e2", "color": "#991b1b"},
}

ARCHIVE_SECTION = {
    "background": "#fffbeb",
    "border": "1px dashed #d97706",
    "borderRadius": "8px",
    "padding": "16px",
    "marginTop": "16px",
}

MODAL_OVERLAY = {
    "position": "fixed",
    "top": "0",
    "left": "0",
    "right": "0",
    "bottom": "0",
    "background": "rgba(0,0,0,0.5)",
    "zIndex": "1000",
    "display": "flex",
    "alignItems": "center",
    "justifyContent": "center",
}

MODAL_CONTENT = {
    "background": "white",
    "borderRadius": "12px",
    "padding": "32px",
    "maxWidth": "700px",
    "width": "90%",
    "maxHeight": "80vh",
    "overflowY": "auto",
    "boxShadow": "0 20px 60px rgba(0,0,0,0.3)",
}

LABEL = {
    "display": "block",
    "marginBottom": "4px",
    "fontSize": "13px",
    "color": "#666",
}

BACK_LINK = {
    "padding": "8px 16px",
    "background": "#f2f4f7",
    "border": "1px solid #e4e8ef",
    "borderRadius": "6px",
    "color": "#1E4EBC",
    "cursor": "pointer",
    "fontSize": "13px",
    "textAlign": "left",
    "fontFamily": "inherit",
}

# ============================================================================
# Layout
# ============================================================================

app.layout = html.Div(
    style={
        "fontFamily": '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
        "background": "#f5f5f5",
        "minHeight": "100vh",
    },
    children=[
        # ---- data stores ---------------------------------------------------
        dcc.Store(id="meetings-data", data=[]),
        dcc.Store(id="selected-meeting", data=None),
        dcc.Store(id="instances-data", data=[]),
        dcc.Store(id="selected-instance", data=None),
        dcc.Store(id="refresh-trigger", data=0),
        dcc.Store(id="current-user-email", data=""),
        dcc.Store(id="is-admin", data=False),
        dcc.Store(id="is-approver", data=False),
        dcc.Store(id="show-archive", data=False),
        dcc.Store(id="managing-meeting", data=None),
        dcc.Store(id="date-mgmt-refresh", data=0),
        dcc.Interval(id="init-interval", interval=500, max_intervals=1),

        # ---- header --------------------------------------------------------
        html.Div(
            style=HEADER,
            children=[
                html.H1(
                    "CDDA Meeting Manager",
                    style={"margin": "0", "fontSize": "28px", "fontWeight": "700"},
                ),
                html.P(
                    "Powered by Microsoft Fabric Lakehouse",
                    style={"margin": "4px 0 0", "opacity": "0.8", "fontSize": "14px"},
                ),
            ],
        ),

        # ---- body ----------------------------------------------------------
        html.Div(
            style=CONTAINER,
            children=[
                # status bar
                html.Div(
                    id="status-bar",
                    style=STATUS_BAR,
                    children=html.Span("⏳ Loading…", style={"color": "#666"}),
                ),

                # ── meetings list view (home) ──────────────────────────────
                html.Div(
                    id="meetings-view",
                    children=[
                        html.H2("Meeting Forums", style={"marginBottom": "16px", "color": "#0B1D3A"}),
                        html.Div(
                            id="meetings-container",
                            children=html.P("Loading meetings…", style={"color": "#666"}),
                        ),
                    ],
                ),

                # ── agenda detail view (two-panel: sidebar + main) ─────────
                html.Div(
                    id="agenda-view",
                    style={"display": "none"},
                    children=[
                        html.Div(
                            style={"display": "flex", "gap": "20px", "minHeight": "calc(100vh - 200px)"},
                            children=[
                                # LEFT SIDEBAR — meeting date instances
                                html.Div(
                                    style=SIDEBAR,
                                    children=[
                                        html.Button(
                                            "← Back to Forums", id="back-btn",
                                            style={
                                                "padding": "12px 16px", "background": "#f2f4f7",
                                                "border": "none", "borderBottom": "1px solid #e4e8ef",
                                                "color": "#1E4EBC", "cursor": "pointer",
                                                "fontSize": "13px", "textAlign": "left",
                                                "fontFamily": "inherit", "width": "100%",
                                            },
                                        ),
                                        html.Div(
                                            id="sidebar-title",
                                            style={
                                                "padding": "14px 16px",
                                                "borderBottom": "1px solid #e4e8ef",
                                                "fontWeight": "700", "fontSize": "15px",
                                                "color": "#0B1D3A",
                                            },
                                        ),
                                        html.Div(
                                            id="sidebar-instances",
                                            style={"flex": "1", "overflowY": "auto", "padding": "6px 0"},
                                        ),
                                    ],
                                ),

                                # RIGHT MAIN PANEL — agenda items
                                html.Div(
                                    style=MAIN_PANEL,
                                    children=[
                                        html.Div(
                                            style={
                                                "padding": "20px 24px",
                                                "borderBottom": "1px solid #e4e8ef",
                                                "display": "flex",
                                                "justifyContent": "space-between",
                                                "alignItems": "center",
                                            },
                                            children=[
                                                html.H2(
                                                    id="agenda-title",
                                                    style={"color": "#0B1D3A", "margin": "0", "fontSize": "20px"},
                                                ),
                                            ],
                                        ),
                                        html.Div(
                                            style={"flex": "1", "overflowY": "auto", "padding": "20px 24px"},
                                            children=[
                                                html.Div(id="time-bar", style={"marginBottom": "20px"}),
                                                html.Div(id="agenda-items"),
                                                # add-item form
                                                html.Div(
                                                    style={
                                                        "background": "#f9fafb",
                                                        "border": "1px dashed #1E4EBC",
                                                        "borderRadius": "8px",
                                                        "padding": "20px",
                                                        "marginTop": "20px",
                                                    },
                                                    children=[
                                                        html.H3(
                                                            "Add Agenda Item",
                                                            style={"marginBottom": "12px", "color": "#0B1D3A", "fontSize": "16px"},
                                                        ),
                                                        dcc.Input(id="inp-title", placeholder="Title *", style=INPUT),
                                                        dcc.Input(id="inp-topic", placeholder="Topic Description", style=INPUT),
                                                        html.Div(
                                                            style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "12px"},
                                                            children=[
                                                                html.Div([
                                                                    html.Label("Duration", style=LABEL),
                                                                    dcc.Dropdown(
                                                                        id="inp-duration",
                                                                        options=[{"label": f"{t} min", "value": t} for t in config.TIME_SLOTS],
                                                                        value=15, clearable=False,
                                                                        style={"marginBottom": "12px"},
                                                                    ),
                                                                ]),
                                                                html.Div([
                                                                    html.Label("Presenter", style=LABEL),
                                                                    dcc.Input(id="inp-presenter", placeholder="Presenter name", style={**INPUT, "marginBottom": "0"}),
                                                                ]),
                                                            ],
                                                        ),
                                                        html.Div(
                                                            style={"display": "flex", "gap": "8px", "justifyContent": "flex-end", "marginTop": "12px"},
                                                            children=[
                                                                html.Button("Add Item", id="add-btn", style=BTN),
                                                            ],
                                                        ),
                                                        html.Div(id="add-feedback", style={"marginTop": "8px"}),
                                                    ],
                                                ),
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),

                # ── date management view ───────────────────────────────────
                html.Div(
                    id="date-mgmt-view",
                    style={"display": "none"},
                    children=[
                        html.H2("Manage Meeting Dates", style={"marginBottom": "16px", "color": "#0B1D3A"}),
                        html.Button(
                            "← Back to Forums",
                            id="date-mgmt-back-btn",
                            style=BACK_LINK,
                        ),
                        html.H3(id="date-mgmt-title", style={"marginTop": "16px", "color": "#0B1D3A"}),

                        # Current dates list
                        html.Div(
                            style=CARD,
                            children=[
                                html.H4("Current Meeting Dates", style={"marginBottom": "12px", "color": "#0B1D3A"}),
                                html.Div(id="current-dates-list"),
                            ],
                        ),

                        # Add Recurring Schedule section
                        html.Div(
                            style=CARD,
                            children=[
                                html.H4("Add Recurring Schedule", style={"marginBottom": "12px", "color": "#0B1D3A"}),
                                html.Div(
                                    style={"display": "grid", "gridTemplateColumns": "1fr 1fr 1fr", "gap": "12px"},
                                    children=[
                                        html.Div([
                                            html.Label("Day of Week", style=LABEL),
                                            dcc.Dropdown(
                                                id="recurring-day",
                                                options=[
                                                    {"label": "Monday", "value": 0},
                                                    {"label": "Tuesday", "value": 1},
                                                    {"label": "Wednesday", "value": 2},
                                                    {"label": "Thursday", "value": 3},
                                                    {"label": "Friday", "value": 4},
                                                    {"label": "Saturday", "value": 5},
                                                    {"label": "Sunday", "value": 6},
                                                ],
                                                placeholder="Select day...",
                                                clearable=False,
                                            ),
                                        ]),
                                        html.Div([
                                            html.Label("Start Date", style=LABEL),
                                            dcc.DatePickerSingle(id="recurring-start", placeholder="Start date"),
                                        ]),
                                        html.Div([
                                            html.Label("End Date", style=LABEL),
                                            dcc.DatePickerSingle(id="recurring-end", placeholder="End date"),
                                        ]),
                                    ],
                                ),
                                html.Div(
                                    style={"display": "flex", "gap": "8px", "marginTop": "12px"},
                                    children=[
                                        html.Button("Generate Dates", id="generate-dates-btn", style=BTN),
                                    ],
                                ),
                                html.Div(id="recurring-feedback", style={"marginTop": "8px"}),
                            ],
                        ),

                        # Add Single Date section
                        html.Div(
                            style=CARD,
                            children=[
                                html.H4("Add Single Date", style={"marginBottom": "12px", "color": "#0B1D3A"}),
                                html.Div(
                                    style={"display": "flex", "gap": "12px", "alignItems": "flex-end"},
                                    children=[
                                        html.Div([
                                            html.Label("Date", style=LABEL),
                                            dcc.DatePickerSingle(id="manual-date", placeholder="Pick a date"),
                                        ]),
                                        html.Button("Add Date", id="add-single-date-btn", style=BTN),
                                    ],
                                ),
                                html.Div(id="manual-date-feedback", style={"marginTop": "8px"}),
                            ],
                        ),
                    ],
                ),
            ],
        ),

        # ---- footer --------------------------------------------------------
        html.Div(
            html.P(
                f"CDDA Meeting Manager  |  {config.APP_ENVIRONMENT}",
                style={"textAlign": "center", "color": "#999", "fontSize": "12px", "padding": "16px"},
            )
        ),
    ],
)

# ============================================================================
# Callbacks
# ============================================================================


# ------ detect current user -------------------------------------------------

@app.callback(
    [
        Output("current-user-email", "data"),
        Output("is-admin", "data"),
        Output("is-approver", "data"),
    ],
    Input("init-interval", "n_intervals"),
)
def detect_user(_n):
    email = _get_current_user()
    return email, _is_admin(email), _is_approver(email)


# ------ load meetings -------------------------------------------------------

@app.callback(
    [Output("meetings-data", "data"), Output("status-bar", "children")],
    [
        Input("init-interval", "n_intervals"),
        Input("refresh-trigger", "data"),
        Input("current-user-email", "data"),
    ],
)
def load_meetings(_n, _r, user_email):
    """Fetch meetings from Fabric (or demo data)."""
    try:
        dl = get_data_layer()
        meetings = dl.get_meetings()
        mode = "Demo Mode" if config.DEMO_MODE else "Live"
        admin_label = " (Admin)" if _is_admin(user_email) else ""
        approver_label = " (Approver)" if _is_approver(user_email) else ""
        role = admin_label or approver_label
        user_display = (
            f" | {user_email}{role}"
            if user_email and user_email != "anonymous"
            else ""
        )
        status = html.Span([
            html.Span("✓ ", style={"color": "#198754"}),
            f"Connected — {len(meetings)} forum(s) loaded ({mode}){user_display}",
        ])
        return meetings, status
    except Exception as exc:
        logger.exception("load_meetings failed")
        return [], html.Span([html.Span("✗ ", style={"color": "#dc3545"}), "An error occurred while loading meetings. Please try again."])


# ------ render meeting cards ------------------------------------------------

@app.callback(
    Output("meetings-container", "children"),
    Input("meetings-data", "data"),
    State("is-admin", "data"),
)
def render_meetings(meetings, is_admin):
    """Build clickable meeting cards with optional admin Manage Dates button."""
    if not meetings:
        return html.P("No meetings found.", style={"color": "#666"})
    cards = []
    for m in meetings:
        card = html.Div(
            id={"type": "mtg-card", "index": m["id"]},
            n_clicks=0,
            style={**CARD, "cursor": "pointer", "marginBottom": "0"},
            children=[
                html.H3(m.get("title", "Untitled"), style={"margin": "0 0 8px", "color": "#0B1D3A"}),
                html.P(m.get("description", ""), style={"color": "#666", "margin": "0 0 12px", "fontSize": "14px"}),
                html.Div([
                    html.Span(f"⏱ {m.get('duration', 60)} min", style={"color": "#1E4EBC", "fontSize": "13px", "marginRight": "16px"}),
                    html.Span(f"{m.get('forum', '').upper()}", style={"color": "#666", "fontSize": "13px"}),
                ]),
            ],
        )

        manage_btn = None
        if is_admin:
            manage_btn = html.Div(
                style={"display": "flex", "justifyContent": "flex-end", "padding": "8px 0 0"},
                children=[
                    html.Button(
                        "⚙ Manage Dates",
                        id={"type": "manage-dates-btn", "index": m["id"]},
                        n_clicks=0,
                        style=BTN_MANAGE,
                    ),
                ],
            )

        wrapper = html.Div(
            style={"marginBottom": "16px"},
            children=[card, manage_btn],
        )
        cards.append(wrapper)
    return cards


# ------ navigate between views ----------------------------------------------

@app.callback(
    [
        Output("selected-meeting", "data"),
        Output("instances-data", "data"),
        Output("selected-instance", "data"),
        Output("meetings-view", "style"),
        Output("agenda-view", "style"),
    ],
    [
        Input({"type": "mtg-card", "index": ALL}, "n_clicks"),
        Input("back-btn", "n_clicks"),
    ],
    State("meetings-data", "data"),
    prevent_initial_call=True,
)
def navigate(card_clicks, _back, meetings):
    """Switch between meetings list and agenda detail; load instances."""
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate

    trigger = ctx.triggered[0]["prop_id"]

    # back button
    if trigger == "back-btn.n_clicks":
        return None, [], None, {"display": "block"}, {"display": "none"}

    # meeting card clicked
    if not any(n for n in card_clicks if n):
        raise PreventUpdate

    tid = json.loads(trigger.split(".")[0])
    mtg = next((m for m in meetings if m["id"] == tid["index"]), None)
    if not mtg:
        raise PreventUpdate

    # Load meeting instances for this forum
    try:
        dl = get_data_layer()
        instances = dl.get_meeting_instances(mtg["id"])
    except Exception:
        instances = []

    # Auto-select first instance
    first_inst = instances[0] if instances else None

    return mtg, instances, first_inst, {"display": "none"}, {"display": "block"}


# ------ sidebar title -------------------------------------------------------

@app.callback(
    Output("sidebar-title", "children"),
    Input("selected-meeting", "data"),
)
def render_sidebar_title(meeting):
    if not meeting:
        return ""
    return meeting.get("title", "")


# ------ sidebar instances ---------------------------------------------------

@app.callback(
    Output("sidebar-instances", "children"),
    [Input("instances-data", "data"), Input("selected-instance", "data")],
)
def render_sidebar(instances, selected):
    """Build the sidebar list of meeting date instances."""
    if not instances:
        return html.P("No meeting dates.", style={"color": "#999", "padding": "16px", "fontSize": "13px"})

    sel_id = selected.get("id") if selected else None
    dl = get_data_layer()
    items = []

    for inst in instances:
        # Count items and time for this instance
        try:
            agenda = dl.get_agenda_items(inst["meeting_id"], instance_id=inst["id"])
        except Exception:
            agenda = []
        item_count = len(agenda)
        time_used = sum(a.get("duration", 0) for a in agenda)

        is_active = inst["id"] == sel_id
        style = SB_ITEM_ACTIVE if is_active else SB_ITEM

        items.append(
            html.Div(
                id={"type": "inst-card", "index": inst["id"]},
                n_clicks=0,
                style=style,
                children=[
                    html.Div(
                        inst.get("display_text", inst.get("date", "")),
                        style={"fontWeight": "600", "fontSize": "14px", "color": "#0B1D3A", "marginBottom": "4px"},
                    ),
                    html.Div(
                        f"{item_count} item{'s' if item_count != 1 else ''}",
                        style={"fontSize": "12px", "color": "#6b7789"},
                    ),
                    html.Div(
                        f"{time_used} min used",
                        style={"fontSize": "12px", "color": "#8a95a6"},
                    ),
                ],
            )
        )
    return items


# ------ select sidebar instance ---------------------------------------------

@app.callback(
    Output("selected-instance", "data", allow_duplicate=True),
    Input({"type": "inst-card", "index": ALL}, "n_clicks"),
    State("instances-data", "data"),
    prevent_initial_call=True,
)
def select_instance(n_clicks, instances):
    """Handle sidebar date click."""
    if not any(n for n in n_clicks if n):
        raise PreventUpdate
    ctx = dash.callback_context
    tid = json.loads(ctx.triggered[0]["prop_id"].split(".")[0])
    inst = next((i for i in instances if i["id"] == tid["index"]), None)
    if not inst:
        raise PreventUpdate
    return inst


# ------ render agenda items -------------------------------------------------

@app.callback(
    [
        Output("agenda-title", "children"),
        Output("time-bar", "children"),
        Output("agenda-items", "children"),
    ],
    [
        Input("selected-instance", "data"),
        Input("selected-meeting", "data"),
        Input("show-archive", "data"),
    ],
    [
        State("is-admin", "data"),
        State("is-approver", "data"),
    ],
)
def render_agenda(instance, meeting, show_archive, is_admin, is_approver):
    """Render agenda items for the selected meeting date instance."""
    if not instance or not meeting:
        raise PreventUpdate

    try:
        dl = get_data_layer()
        items = dl.get_agenda_items(meeting["id"], instance_id=instance["id"])
    except Exception:
        items = []

    # Title
    title = f"Agenda Items — {instance.get('display_text', '')}"

    # Time bar
    total = meeting.get("duration", 60)
    used = sum(i.get("duration", 0) for i in items)
    remaining = total - used
    pct = min(100, used / total * 100) if total else 0
    bar_color = "#198754" if remaining > 15 else "#ffc107" if remaining > 0 else "#dc3545"

    time_bar = html.Div([
        html.Div([
            html.Span(f"Time: {used}/{total} min used", style={"fontSize": "13px"}),
            html.Span(
                f"{remaining} min remaining",
                style={"fontSize": "13px", "fontWeight": "600", "color": bar_color},
            ),
        ], style={"display": "flex", "justifyContent": "space-between", "marginBottom": "4px"}),
        html.Div(
            html.Div(
                style={
                    "width": f"{pct}%",
                    "height": "8px",
                    "background": bar_color,
                    "borderRadius": "4px",
                    "transition": "width 0.3s",
                },
            ),
            style={"background": "#e9ecef", "borderRadius": "4px", "overflow": "hidden"},
        ),
    ])

    # Agenda item cards with documents, status badges, and role-based buttons
    if not items:
        rows_el = html.P(
            "No agenda items for this date. Add one below.",
            style={"color": "#666", "padding": "20px 0"},
        )
    else:
        rows = []
        for item in items:
            # Status badge
            status = item.get("status", "Pending")
            badge_style = {
                **BADGE_STYLES.get(status, BADGE_STYLES["Pending"]),
                "display": "inline-block",
                "padding": "2px 10px",
                "borderRadius": "12px",
                "fontSize": "11px",
                "fontWeight": "600",
                "marginLeft": "8px",
            }

            # Load documents for this item
            try:
                docs = dl.get_documents(item["id"])
            except Exception:
                docs = []

            doc_chips = []
            for doc in docs:
                ext = doc.get("doc_type", "file").lower()
                icon = "📄" if ext == "pdf" else "📊" if ext in ("xlsx", "xls", "csv") else "📎"
                doc_chips.append(
                    html.Span(f"{icon} {doc.get('filename', 'document')}", style=DOC_CHIP)
                )

            # Conditional buttons based on role
            buttons = []
            if is_approver and status != "Approved":
                buttons.append(
                    html.Button(
                        "✓ Approve",
                        id={"type": "approve-btn", "index": item["id"]},
                        n_clicks=0,
                        style=BTN_OK,
                    )
                )
            if is_admin:
                buttons.append(
                    html.Button(
                        "📦 Archive",
                        id={"type": "archive-btn", "index": item["id"]},
                        n_clicks=0,
                        style=BTN_ARCHIVE,
                    )
                )

            button_section = (
                html.Div(
                    style={"display": "flex", "gap": "8px", "alignItems": "center", "marginLeft": "12px"},
                    children=buttons,
                )
                if buttons
                else None
            )

            rows.append(
                html.Div(
                    style={**CARD, "cursor": "default", "display": "flex", "alignItems": "flex-start"},
                    children=[
                        html.Div(
                            style={"flex": "1"},
                            children=[
                                html.Div(
                                    [
                                        html.H4(
                                            item.get("title", "Untitled"),
                                            style={"margin": "0", "color": "#0B1D3A", "display": "inline"},
                                        ),
                                        html.Span(status, style=badge_style),
                                    ],
                                    style={"marginBottom": "4px"},
                                ),
                                (
                                    html.P(
                                        item.get("topic", ""),
                                        style={"color": "#666", "margin": "0 0 8px", "fontSize": "14px"},
                                    )
                                    if item.get("topic")
                                    else None
                                ),
                                html.Div([
                                    html.Span(
                                        f"⏱ {item.get('duration', 0)} min",
                                        style={"marginRight": "16px", "fontSize": "13px", "color": "#1E4EBC"},
                                    ),
                                    html.Span(
                                        f"👤 {item.get('presenter', 'TBD')}",
                                        style={"fontSize": "13px", "color": "#666"},
                                    ),
                                ]),
                                (
                                    html.Div(doc_chips, style={"marginTop": "8px"})
                                    if doc_chips
                                    else None
                                ),
                            ],
                        ),
                        button_section,
                    ],
                )
            )
        rows_el = html.Div(rows)

    # Archive section (admin only)
    archive_section = None
    if is_admin:
        try:
            archived = dl.get_archived_items(meeting["id"], instance_id=instance["id"])
        except Exception:
            archived = []
        archive_count = len(archived)

        archive_toggle = html.Button(
            f"📦 {'Hide' if show_archive else 'Show'} Archive ({archive_count})",
            id="toggle-archive-btn",
            n_clicks=0,
            style={**BTN, "background": "#78716c", "fontSize": "13px"},
        )

        archived_cards = []
        if show_archive and archived:
            for aitem in archived:
                archived_cards.append(
                    html.Div(
                        style={
                            **CARD,
                            "opacity": "0.7",
                            "borderLeft": "3px solid #d97706",
                            "display": "flex",
                            "alignItems": "flex-start",
                        },
                        children=[
                            html.Div(
                                style={"flex": "1"},
                                children=[
                                    html.H4(
                                        aitem.get("title", ""),
                                        style={"margin": "0 0 4px", "color": "#78716c"},
                                    ),
                                    html.Div([
                                        html.Span(
                                            f"⏱ {aitem.get('duration', 0)} min",
                                            style={"fontSize": "13px", "color": "#a1a1aa"},
                                        ),
                                    ]),
                                ],
                            ),
                            html.Button(
                                "↩ Restore",
                                id={"type": "restore-btn", "index": aitem["id"]},
                                n_clicks=0,
                                style=BTN_RESTORE,
                            ),
                        ],
                    )
                )

        archive_section = html.Div(
            style=ARCHIVE_SECTION if (archive_count > 0 or show_archive) else {"display": "none"},
            children=[archive_toggle] + archived_cards,
        )

    items_el = html.Div([rows_el, archive_section])

    return title, time_bar, items_el


# ------ add agenda item -----------------------------------------------------

@app.callback(
    [
        Output("add-feedback", "children"),
        Output("selected-instance", "data", allow_duplicate=True),
        Output("inp-title", "value"),
        Output("inp-topic", "value"),
        Output("inp-presenter", "value"),
    ],
    Input("add-btn", "n_clicks"),
    [
        State("inp-title", "value"),
        State("inp-topic", "value"),
        State("inp-duration", "value"),
        State("inp-presenter", "value"),
        State("selected-meeting", "data"),
        State("selected-instance", "data"),
    ],
    prevent_initial_call=True,
)
def add_item(n, title, topic, duration, presenter, meeting, instance):
    """Add agenda item to the selected meeting date."""
    if not n or not meeting or not instance:
        raise PreventUpdate
    user = _get_current_user()
    if user == "anonymous":
        return (
            html.Span("Authentication required to add items.", style={"color": "#dc3545"}),
            no_update,
            no_update,
            no_update,
            no_update,
        )
    if not title:
        return (
            html.Span("Please enter a title.", style={"color": "#dc3545"}),
            no_update,
            no_update,
            no_update,
            no_update,
        )
    try:
        dl = get_data_layer()
        dl.create_agenda_item(
            meeting["id"],
            title,
            topic or "",
            duration or 15,
            presenter or "",
            instance_id=instance.get("id") if instance else None,
        )
        refreshed = {**instance, "_r": instance.get("_r", 0) + 1}
        return html.Span("✓ Item added!", style={"color": "#198754"}), refreshed, "", "", ""
    except Exception as exc:
        logger.exception("add_item failed")
        return (
            html.Span("An error occurred. Please try again.", style={"color": "#dc3545"}),
            no_update,
            no_update,
            no_update,
            no_update,
        )


# ------ archive agenda item (was delete) ------------------------------------

@app.callback(
    Output("selected-instance", "data", allow_duplicate=True),
    Input({"type": "archive-btn", "index": ALL}, "n_clicks"),
    State("selected-instance", "data"),
    prevent_initial_call=True,
)
def archive_item(n_clicks, instance):
    """Archive an agenda item (soft delete)."""
    if not any(n for n in n_clicks if n) or not instance:
        raise PreventUpdate
    user = _get_current_user()
    if not _is_admin(user):
        raise PreventUpdate
    ctx = dash.callback_context
    tid = json.loads(ctx.triggered[0]["prop_id"].split(".")[0])
    try:
        dl = get_data_layer()
        dl.archive_agenda_item(tid["index"])
    except Exception:
        pass
    return {**instance, "_r": instance.get("_r", 0) + 1}


# ------ approve agenda item -------------------------------------------------

@app.callback(
    Output("selected-instance", "data", allow_duplicate=True),
    Input({"type": "approve-btn", "index": ALL}, "n_clicks"),
    State("selected-instance", "data"),
    prevent_initial_call=True,
)
def approve_item(n_clicks, instance):
    """Approve an agenda item."""
    if not any(n for n in n_clicks if n) or not instance:
        raise PreventUpdate
    user = _get_current_user()
    if not _is_approver(user):
        raise PreventUpdate
    ctx = dash.callback_context
    tid = json.loads(ctx.triggered[0]["prop_id"].split(".")[0])
    try:
        dl = get_data_layer()
        dl.set_approval(tid["index"], user, True)
    except Exception:
        pass
    return {**instance, "_r": instance.get("_r", 0) + 1}


# ------ restore archived item -----------------------------------------------

@app.callback(
    Output("selected-instance", "data", allow_duplicate=True),
    Input({"type": "restore-btn", "index": ALL}, "n_clicks"),
    State("selected-instance", "data"),
    prevent_initial_call=True,
)
def restore_item(n_clicks, instance):
    """Restore an archived agenda item."""
    if not any(n for n in n_clicks if n) or not instance:
        raise PreventUpdate
    user = _get_current_user()
    if not _is_admin(user):
        raise PreventUpdate
    ctx = dash.callback_context
    tid = json.loads(ctx.triggered[0]["prop_id"].split(".")[0])
    try:
        dl = get_data_layer()
        dl.restore_agenda_item(tid["index"])
    except Exception:
        pass
    return {**instance, "_r": instance.get("_r", 0) + 1}


# ------ toggle archive section visibility -----------------------------------

@app.callback(
    Output("show-archive", "data"),
    Input("toggle-archive-btn", "n_clicks"),
    State("show-archive", "data"),
    prevent_initial_call=True,
)
def toggle_archive(n, current):
    if not n:
        raise PreventUpdate
    return not current


# ------ open date management view -------------------------------------------

@app.callback(
    [
        Output("managing-meeting", "data"),
        Output("meetings-view", "style", allow_duplicate=True),
        Output("date-mgmt-view", "style"),
    ],
    Input({"type": "manage-dates-btn", "index": ALL}, "n_clicks"),
    State("meetings-data", "data"),
    prevent_initial_call=True,
)
def open_date_manager(n_clicks, meetings):
    if not any(n for n in n_clicks if n):
        raise PreventUpdate
    user = _get_current_user()
    if not _is_admin(user):
        raise PreventUpdate
    ctx = dash.callback_context
    tid = json.loads(ctx.triggered[0]["prop_id"].split(".")[0])
    mtg = next((m for m in meetings if m["id"] == tid["index"]), None)
    return mtg, {"display": "none"}, {"display": "block"}


# ------ close date management view ------------------------------------------

@app.callback(
    [
        Output("managing-meeting", "data", allow_duplicate=True),
        Output("meetings-view", "style", allow_duplicate=True),
        Output("date-mgmt-view", "style", allow_duplicate=True),
    ],
    Input("date-mgmt-back-btn", "n_clicks"),
    prevent_initial_call=True,
)
def close_date_manager(n):
    if not n:
        raise PreventUpdate
    return None, {"display": "block"}, {"display": "none"}


# ------ render date management title ----------------------------------------

@app.callback(
    Output("date-mgmt-title", "children"),
    Input("managing-meeting", "data"),
)
def render_date_mgmt_title(meeting):
    if not meeting:
        return ""
    return meeting.get("title", "")


# ------ render current dates list -------------------------------------------

@app.callback(
    Output("current-dates-list", "children"),
    [Input("managing-meeting", "data"), Input("date-mgmt-refresh", "data")],
    State("is-admin", "data"),
)
def render_current_dates(meeting, _refresh, is_admin):
    """List all scheduled dates for the managed meeting with delete buttons."""
    if not meeting:
        return html.P("No meeting selected.", style={"color": "#666"})
    try:
        dl = get_data_layer()
        instances = dl.get_meeting_instances(meeting["id"])
    except Exception:
        instances = []
    if not instances:
        return html.P("No dates scheduled yet.", style={"color": "#666", "fontStyle": "italic"})

    rows = []
    for inst in instances:
        row_children = [
            html.Span(
                inst.get("display_text", inst.get("date", "")),
                style={"fontWeight": "600", "fontSize": "14px", "color": "#0B1D3A"},
            ),
        ]
        if is_admin:
            row_children.append(
                html.Button(
                    "🗑 Remove",
                    id={"type": "delete-date-btn", "index": inst["id"]},
                    n_clicks=0,
                    style={**BTN_DEL, "padding": "4px 12px", "fontSize": "12px"},
                )
            )
        rows.append(
            html.Div(
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "center",
                    "padding": "8px 12px",
                    "borderBottom": "1px solid #f0f0f0",
                },
                children=row_children,
            )
        )
    return html.Div(rows)


# ------ generate recurring dates --------------------------------------------

@app.callback(
    [
        Output("recurring-feedback", "children"),
        Output("date-mgmt-refresh", "data", allow_duplicate=True),
    ],
    Input("generate-dates-btn", "n_clicks"),
    [
        State("recurring-day", "value"),
        State("recurring-start", "date"),
        State("recurring-end", "date"),
        State("managing-meeting", "data"),
        State("date-mgmt-refresh", "data"),
    ],
    prevent_initial_call=True,
)
def gen_recurring_dates(n, day, start, end, meeting, refresh):
    if not n or not meeting:
        raise PreventUpdate
    user = _get_current_user()
    if not _is_admin(user):
        raise PreventUpdate
    if day is None or not start or not end:
        return (
            html.Span("Please select day of week, start date, and end date.", style={"color": "#dc3545"}),
            no_update,
        )
    try:
        dates = generate_recurring_dates(day, start[:10], end[:10])
        if not dates:
            return (
                html.Span("No dates generated for this range.", style={"color": "#ffc107"}),
                no_update,
            )
        dl = get_data_layer()
        created = dl.create_meeting_instances_bulk(meeting["id"], dates)
        return (
            html.Span(f"✓ {len(created)} date(s) added!", style={"color": "#198754"}),
            refresh + 1,
        )
    except Exception as exc:
        logger.exception("gen_recurring_dates failed")
        return html.Span("An error occurred. Please try again.", style={"color": "#dc3545"}), no_update


# ------ add single date -----------------------------------------------------

@app.callback(
    [
        Output("manual-date-feedback", "children"),
        Output("date-mgmt-refresh", "data", allow_duplicate=True),
    ],
    Input("add-single-date-btn", "n_clicks"),
    [
        State("manual-date", "date"),
        State("managing-meeting", "data"),
        State("date-mgmt-refresh", "data"),
    ],
    prevent_initial_call=True,
)
def add_single_date(n, date_val, meeting, refresh):
    if not n or not meeting:
        raise PreventUpdate
    user = _get_current_user()
    if not _is_admin(user):
        raise PreventUpdate
    if not date_val:
        return (
            html.Span("Please select a date.", style={"color": "#dc3545"}),
            no_update,
        )
    try:
        dt = datetime.strptime(date_val[:10], "%Y-%m-%d")
        display_text = dt.strftime("%d %b %Y")
        dl = get_data_layer()
        dl.create_meeting_instance(meeting["id"], date_val[:10], display_text)
        return (
            html.Span(f"✓ Date {display_text} added!", style={"color": "#198754"}),
            refresh + 1,
        )
    except Exception as exc:
        logger.exception("add_single_date failed")
        return html.Span("An error occurred. Please try again.", style={"color": "#dc3545"}), no_update


# ------ delete meeting date -------------------------------------------------

@app.callback(
    Output("date-mgmt-refresh", "data", allow_duplicate=True),
    Input({"type": "delete-date-btn", "index": ALL}, "n_clicks"),
    State("date-mgmt-refresh", "data"),
    prevent_initial_call=True,
)
def delete_date(n_clicks, refresh):
    if not any(n for n in n_clicks if n):
        raise PreventUpdate
    user = _get_current_user()
    if not _is_admin(user):
        raise PreventUpdate
    ctx = dash.callback_context
    tid = json.loads(ctx.triggered[0]["prop_id"].split(".")[0])
    try:
        dl = get_data_layer()
        dl.delete_meeting_instance(tid["index"], cascade=True)
    except Exception:
        pass
    return refresh + 1


# ============================================================================
# Local dev
# ============================================================================

if __name__ == "__main__":
    app.run(debug=True, port=8050)
