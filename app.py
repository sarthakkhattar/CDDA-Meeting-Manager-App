"""
CDDA Meeting Manager — Dash Application.
Deployed on Posit Connect as python-dash.

Entrypoint: app:server
"""

import dash
from dash import html, dcc, Input, Output, State, no_update, ALL
from dash.exceptions import PreventUpdate
import json

import config
from fabric_graph import get_data_layer

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
                                                                    html.Label("Duration", style={"display": "block", "marginBottom": "4px", "fontSize": "13px", "color": "#666"}),
                                                                    dcc.Dropdown(
                                                                        id="inp-duration",
                                                                        options=[{"label": f"{t} min", "value": t} for t in config.TIME_SLOTS],
                                                                        value=15, clearable=False,
                                                                        style={"marginBottom": "12px"},
                                                                    ),
                                                                ]),
                                                                html.Div([
                                                                    html.Label("Presenter", style={"display": "block", "marginBottom": "4px", "fontSize": "13px", "color": "#666"}),
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


@app.callback(
    [Output("meetings-data", "data"), Output("status-bar", "children")],
    [Input("init-interval", "n_intervals"), Input("refresh-trigger", "data")],
)
def load_meetings(_n, _r):
    """Fetch meetings from Fabric (or demo data)."""
    try:
        dl = get_data_layer()
        meetings = dl.get_meetings()
        mode = "Demo Mode" if config.DEMO_MODE else "Live"
        status = html.Span([
            html.Span("✓ ", style={"color": "#198754"}),
            f"Connected — {len(meetings)} forum(s) loaded ({mode})",
        ])
        return meetings, status
    except Exception as exc:
        return [], html.Span([html.Span("✗ ", style={"color": "#dc3545"}), f"Error: {exc}"])


@app.callback(
    Output("meetings-container", "children"),
    Input("meetings-data", "data"),
)
def render_meetings(meetings):
    """Build clickable meeting cards."""
    if not meetings:
        return html.P("No meetings found.", style={"color": "#666"})
    cards = []
    for m in meetings:
        cards.append(
            html.Div(
                id={"type": "mtg-card", "index": m["id"]},
                n_clicks=0,
                style={**CARD, "cursor": "pointer"},
                children=[
                    html.H3(m.get("title", "Untitled"), style={"margin": "0 0 8px", "color": "#0B1D3A"}),
                    html.P(m.get("description", ""), style={"color": "#666", "margin": "0 0 12px", "fontSize": "14px"}),
                    html.Div([
                        html.Span(f"⏱ {m.get('duration', 60)} min", style={"color": "#1E4EBC", "fontSize": "13px", "marginRight": "16px"}),
                        html.Span(f"📋 {m.get('forum', '').upper()}", style={"color": "#666", "fontSize": "13px"}),
                    ]),
                ],
            )
        )
    return cards


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


@app.callback(
    Output("sidebar-title", "children"),
    Input("selected-meeting", "data"),
)
def render_sidebar_title(meeting):
    if not meeting:
        return ""
    return meeting.get("title", "")


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


@app.callback(
    [
        Output("agenda-title", "children"),
        Output("time-bar", "children"),
        Output("agenda-items", "children"),
    ],
    [Input("selected-instance", "data"), Input("selected-meeting", "data")],
)
def render_agenda(instance, meeting):
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
            html.Span(f"{remaining} min remaining", style={"fontSize": "13px", "fontWeight": "600", "color": bar_color}),
        ], style={"display": "flex", "justifyContent": "space-between", "marginBottom": "4px"}),
        html.Div(
            html.Div(style={"width": f"{pct}%", "height": "8px", "background": bar_color, "borderRadius": "4px", "transition": "width 0.3s"}),
            style={"background": "#e9ecef", "borderRadius": "4px", "overflow": "hidden"},
        ),
    ])

    # Agenda item cards with documents
    if not items:
        items_el = html.P("No agenda items for this date. Add one below.", style={"color": "#666", "padding": "20px 0"})
    else:
        rows = []
        for item in items:
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
                    html.Span(
                        f"{icon} {doc.get('filename', 'document')}",
                        style=DOC_CHIP,
                    )
                )

            rows.append(
                html.Div(
                    style={**CARD, "cursor": "default", "display": "flex", "alignItems": "flex-start"},
                    children=[
                        html.Div(
                            style={"flex": "1"},
                            children=[
                                html.H4(item.get("title", "Untitled"), style={"margin": "0 0 4px", "color": "#0B1D3A"}),
                                html.P(
                                    item.get("topic", ""),
                                    style={"color": "#666", "margin": "0 0 8px", "fontSize": "14px"},
                                ) if item.get("topic") else None,
                                html.Div([
                                    html.Span(f"⏱ {item.get('duration', 0)} min", style={"marginRight": "16px", "fontSize": "13px", "color": "#1E4EBC"}),
                                    html.Span(f"👤 {item.get('presenter', 'TBD')}", style={"fontSize": "13px", "color": "#666"}),
                                ]),
                                # Document attachments
                                html.Div(
                                    doc_chips,
                                    style={"marginTop": "8px"},
                                ) if doc_chips else None,
                            ],
                        ),
                        html.Div(
                            style={"display": "flex", "gap": "8px", "alignItems": "center", "marginLeft": "12px"},
                            children=[
                                html.Button("✓ Approve", id={"type": "approve-btn", "index": item["id"]}, n_clicks=0, style=BTN_OK),
                                html.Button("✕ Delete", id={"type": "delete-btn", "index": item["id"]}, n_clicks=0, style=BTN_DEL),
                            ],
                        ),
                    ],
                )
            )
        items_el = html.Div(rows)

    return title, time_bar, items_el


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
    if not title:
        return html.Span("Please enter a title.", style={"color": "#dc3545"}), no_update, no_update, no_update, no_update
    try:
        dl = get_data_layer()
        dl.create_agenda_item(
            meeting["id"], title, topic or "", duration or 15, presenter or "",
            instance_id=instance.get("id") if instance else None,
        )
        refreshed = {**instance, "_r": instance.get("_r", 0) + 1}
        return html.Span("✓ Item added!", style={"color": "#198754"}), refreshed, "", "", ""
    except Exception as exc:
        return html.Span(f"Error: {exc}", style={"color": "#dc3545"}), no_update, no_update, no_update, no_update


@app.callback(
    Output("selected-instance", "data", allow_duplicate=True),
    Input({"type": "delete-btn", "index": ALL}, "n_clicks"),
    State("selected-instance", "data"),
    prevent_initial_call=True,
)
def delete_item(n_clicks, instance):
    """Delete an agenda item."""
    if not any(n for n in n_clicks if n) or not instance:
        raise PreventUpdate
    ctx = dash.callback_context
    tid = json.loads(ctx.triggered[0]["prop_id"].split(".")[0])
    try:
        dl = get_data_layer()
        dl.delete_agenda_item(tid["index"])
    except Exception:
        pass
    return {**instance, "_r": instance.get("_r", 0) + 1}


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
    ctx = dash.callback_context
    tid = json.loads(ctx.triggered[0]["prop_id"].split(".")[0])
    try:
        dl = get_data_layer()
        dl.set_approval(tid["index"], "current_user", True)
    except Exception:
        pass
    return {**instance, "_r": instance.get("_r", 0) + 1}


# ============================================================================
# Local dev
# ============================================================================

if __name__ == "__main__":
    app.run(debug=True, port=8050)
