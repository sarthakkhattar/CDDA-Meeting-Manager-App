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
    "maxWidth": "1200px",
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
        dcc.Store(id="agenda-data", data=[]),
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
                # status
                html.Div(
                    id="status-bar",
                    style=STATUS_BAR,
                    children=html.Span("⏳ Loading…", style={"color": "#666"}),
                ),

                # ── meetings list view ──────────────────────────────────────
                html.Div(
                    id="meetings-view",
                    children=[
                        html.H2(
                            "Meeting Forums",
                            style={"marginBottom": "16px", "color": "#0B1D3A"},
                        ),
                        html.Div(
                            id="meetings-container",
                            children=html.P(
                                "Loading meetings…", style={"color": "#666"}
                            ),
                        ),
                    ],
                ),

                # ── agenda detail view (hidden initially) ───────────────────
                html.Div(
                    id="agenda-view",
                    style={"display": "none"},
                    children=[
                        html.Button(
                            "← Back to Meetings", id="back-btn", style=BTN_BACK
                        ),
                        html.Div(
                            style={"marginTop": "16px"},
                            children=[
                                html.H2(
                                    id="agenda-title",
                                    style={"color": "#0B1D3A", "marginBottom": "4px"},
                                ),
                                html.P(
                                    id="agenda-desc",
                                    style={"color": "#666", "marginBottom": "8px"},
                                ),
                                html.Div(id="time-bar", style={"marginBottom": "24px"}),
                            ],
                        ),
                        html.Div(id="agenda-items"),

                        # add-item form
                        html.Div(
                            style={**CARD, "marginTop": "24px", "cursor": "default"},
                            children=[
                                html.H3(
                                    "Add Agenda Item",
                                    style={
                                        "marginBottom": "12px",
                                        "color": "#0B1D3A",
                                    },
                                ),
                                dcc.Input(
                                    id="inp-title",
                                    placeholder="Title *",
                                    style=INPUT,
                                ),
                                dcc.Input(
                                    id="inp-topic",
                                    placeholder="Topic Description",
                                    style=INPUT,
                                ),
                                html.Div(
                                    [
                                        html.Label(
                                            "Duration (minutes)",
                                            style={
                                                "display": "block",
                                                "marginBottom": "4px",
                                                "fontSize": "14px",
                                                "color": "#666",
                                            },
                                        ),
                                        dcc.Dropdown(
                                            id="inp-duration",
                                            options=[
                                                {"label": f"{t} min", "value": t}
                                                for t in config.TIME_SLOTS
                                            ],
                                            value=15,
                                            clearable=False,
                                            style={"marginBottom": "12px"},
                                        ),
                                    ]
                                ),
                                dcc.Input(
                                    id="inp-presenter",
                                    placeholder="Presenter",
                                    style=INPUT,
                                ),
                                html.Button("Add Item", id="add-btn", style=BTN),
                                html.Div(
                                    id="add-feedback", style={"marginTop": "8px"}
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
                style={
                    "textAlign": "center",
                    "color": "#999",
                    "fontSize": "12px",
                    "padding": "16px",
                },
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
        status = html.Span(
            [
                html.Span("✓ ", style={"color": "#198754"}),
                f"Connected — {len(meetings)} forum(s) loaded ({mode})",
            ]
        )
        return meetings, status
    except Exception as exc:
        status = html.Span(
            [html.Span("✗ ", style={"color": "#dc3545"}), f"Error: {exc}"]
        )
        return [], status


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
                    html.H3(
                        m.get("title", "Untitled"),
                        style={"margin": "0 0 8px", "color": "#0B1D3A"},
                    ),
                    html.P(
                        m.get("description", ""),
                        style={
                            "color": "#666",
                            "margin": "0 0 12px",
                            "fontSize": "14px",
                        },
                    ),
                    html.Div(
                        [
                            html.Span(
                                f"⏱ {m.get('duration', 60)} min",
                                style={
                                    "color": "#1E4EBC",
                                    "fontSize": "13px",
                                    "marginRight": "16px",
                                },
                            ),
                            html.Span(
                                f"📋 {m.get('forum', '').upper()}",
                                style={"color": "#666", "fontSize": "13px"},
                            ),
                        ]
                    ),
                ],
            )
        )
    return cards


@app.callback(
    [
        Output("selected-meeting", "data"),
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
    """Switch between meetings list and agenda detail."""
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate

    trigger = ctx.triggered[0]["prop_id"]

    # back button
    if trigger == "back-btn.n_clicks":
        return None, {"display": "block"}, {"display": "none"}

    # meeting card
    if not any(n for n in card_clicks if n):
        raise PreventUpdate

    tid = json.loads(trigger.split(".")[0])
    mtg = next((m for m in meetings if m["id"] == tid["index"]), None)
    if not mtg:
        raise PreventUpdate

    return mtg, {"display": "none"}, {"display": "block"}


@app.callback(
    [
        Output("agenda-title", "children"),
        Output("agenda-desc", "children"),
        Output("time-bar", "children"),
        Output("agenda-items", "children"),
    ],
    Input("selected-meeting", "data"),
)
def render_agenda(meeting):
    """Render agenda items for the selected meeting."""
    if not meeting:
        raise PreventUpdate

    try:
        dl = get_data_layer()
        items = dl.get_agenda_items(meeting["id"])
    except Exception:
        items = []

    total = meeting.get("duration", 60)
    used = sum(i.get("duration", 0) for i in items)
    remaining = total - used
    pct = min(100, used / total * 100) if total else 0
    bar_color = "#198754" if remaining > 15 else "#ffc107" if remaining > 0 else "#dc3545"

    time_bar = html.Div(
        [
            html.Div(
                [
                    html.Span(f"Time: {used}/{total} min used", style={"fontSize": "13px"}),
                    html.Span(
                        f"{remaining} min remaining",
                        style={"fontSize": "13px", "fontWeight": "600", "color": bar_color},
                    ),
                ],
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "marginBottom": "4px",
                },
            ),
            html.Div(
                html.Div(
                    style={
                        "width": f"{pct}%",
                        "height": "8px",
                        "background": bar_color,
                        "borderRadius": "4px",
                        "transition": "width 0.3s",
                    }
                ),
                style={
                    "background": "#e9ecef",
                    "borderRadius": "4px",
                    "overflow": "hidden",
                },
            ),
        ]
    )

    if not items:
        items_el = html.P(
            "No agenda items yet. Add one below.",
            style={"color": "#666", "padding": "20px 0"},
        )
    else:
        rows = []
        for item in items:
            rows.append(
                html.Div(
                    style={**CARD, "cursor": "default", "display": "flex", "alignItems": "center"},
                    children=[
                        html.Div(
                            style={"flex": "1"},
                            children=[
                                html.H4(
                                    item.get("title", "Untitled"),
                                    style={"margin": "0 0 4px", "color": "#0B1D3A"},
                                ),
                                html.P(
                                    item.get("topic", ""),
                                    style={
                                        "color": "#666",
                                        "margin": "0 0 8px",
                                        "fontSize": "14px",
                                    },
                                ),
                                html.Div(
                                    [
                                        html.Span(
                                            f"⏱ {item.get('duration', 0)} min",
                                            style={
                                                "marginRight": "16px",
                                                "fontSize": "13px",
                                                "color": "#1E4EBC",
                                            },
                                        ),
                                        html.Span(
                                            f"👤 {item.get('presenter', 'TBD')}",
                                            style={"fontSize": "13px", "color": "#666"},
                                        ),
                                    ]
                                ),
                            ],
                        ),
                        html.Div(
                            style={"display": "flex", "gap": "8px", "alignItems": "center"},
                            children=[
                                html.Button(
                                    "✓ Approve",
                                    id={"type": "approve-btn", "index": item["id"]},
                                    n_clicks=0,
                                    style=BTN_OK,
                                ),
                                html.Button(
                                    "✕ Delete",
                                    id={"type": "delete-btn", "index": item["id"]},
                                    n_clicks=0,
                                    style=BTN_DEL,
                                ),
                            ],
                        ),
                    ],
                )
            )
        items_el = html.Div(rows)

    return meeting.get("title", "Meeting"), meeting.get("description", ""), time_bar, items_el


@app.callback(
    [
        Output("add-feedback", "children"),
        Output("selected-meeting", "data", allow_duplicate=True),
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
    ],
    prevent_initial_call=True,
)
def add_item(n, title, topic, duration, presenter, meeting):
    """Add agenda item to the selected meeting."""
    if not n or not meeting:
        raise PreventUpdate
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
            meeting["id"], title, topic or "", duration or 15, presenter or ""
        )
        refreshed = {**meeting, "_r": meeting.get("_r", 0) + 1}
        return (
            html.Span("✓ Item added!", style={"color": "#198754"}),
            refreshed,
            "",
            "",
            "",
        )
    except Exception as exc:
        return (
            html.Span(f"Error: {exc}", style={"color": "#dc3545"}),
            no_update,
            no_update,
            no_update,
            no_update,
        )


@app.callback(
    Output("selected-meeting", "data", allow_duplicate=True),
    Input({"type": "delete-btn", "index": ALL}, "n_clicks"),
    State("selected-meeting", "data"),
    prevent_initial_call=True,
)
def delete_item(n_clicks, meeting):
    """Delete an agenda item."""
    if not any(n for n in n_clicks if n) or not meeting:
        raise PreventUpdate
    ctx = dash.callback_context
    tid = json.loads(ctx.triggered[0]["prop_id"].split(".")[0])
    try:
        dl = get_data_layer()
        dl.delete_agenda_item(tid["index"])
    except Exception:
        pass
    return {**meeting, "_r": meeting.get("_r", 0) + 1}


@app.callback(
    Output("selected-meeting", "data", allow_duplicate=True),
    Input({"type": "approve-btn", "index": ALL}, "n_clicks"),
    State("selected-meeting", "data"),
    prevent_initial_call=True,
)
def approve_item(n_clicks, meeting):
    """Approve an agenda item."""
    if not any(n for n in n_clicks if n) or not meeting:
        raise PreventUpdate
    ctx = dash.callback_context
    tid = json.loads(ctx.triggered[0]["prop_id"].split(".")[0])
    try:
        dl = get_data_layer()
        dl.set_approval(tid["index"], "current_user", True)
    except Exception:
        pass
    return {**meeting, "_r": meeting.get("_r", 0) + 1}


# ============================================================================
# Health route on the underlying Flask server
# ============================================================================

@server.route("/health")
def health_check():
    import json as jlib

    return (
        jlib.dumps(
            {
                "status": "ok",
                "app": "CDDA Meeting Manager",
                "mode": "demo" if config.DEMO_MODE else "live",
                "environment": config.APP_ENVIRONMENT,
            }
        ),
        200,
        {"Content-Type": "application/json"},
    )


# ============================================================================
# Local dev
# ============================================================================

if __name__ == "__main__":
    app.run(debug=True, port=8050)
