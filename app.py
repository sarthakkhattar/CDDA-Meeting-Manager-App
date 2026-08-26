"""
CDDA Meeting Manager - Dash port of the CDDA_Meeting_Manager_V2_DEV Power App.

Entrypoint for Posit Connect is ``app:server`` (app mode python-dash).

Screens
-------
home    Forum picker, one card per CDDAMeetings row.
agenda  Meeting-date rail on the left, agenda items for the selected date on the
        right, with add / delete / approve and per-item document upload.

The behaviour mirrors the Power App:
  * meeting dates              Filter(MeetingInstances, MeetingName.Id = forum.ID)
  * agenda items for a date    Filter(AgendaItems, MeetingDateCol = instance date)
  * time remaining             forum.MeetingDuration - Sum(items, TimeRequired)
  * duration choices           colTimes limited to the time still available
  * approve                    Patch(AgendaItems, ..., {Status:"Approved"}),
                               visible only to APPROVER_EMAILS
  * delete an item             removes its Documents rows first, then the item
"""

from __future__ import annotations

import base64
import datetime as _dt
import logging

import dash
from dash import ALL, Input, Output, State, dcc, html, no_update

import config
import sharepoint_client as sp
import theme as t
from ad_access import enforce_access, get_current_email, get_current_user

logging.basicConfig(
    level=logging.DEBUG if config.DEBUG_LOGGING else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("cdda")

app = dash.Dash(
    __name__,
    title="CDDA Meeting Manager",
    update_title=None,
    suppress_callback_exceptions=True,
)
server = app.server          # <- Posit Connect entrypoint: app:server
enforce_access(server)

app.index_string = f"""<!DOCTYPE html>
<html>
  <head>
    {{%metas%}}<title>{{%title%}}</title>{{%favicon%}}{{%css%}}
    <style>{t.INDEX_CSS}</style>
  </head>
  <body>
    {{%app_entry%}}
    <footer>{{%config%}}{{%scripts%}}{{%renderer%}}</footer>
  </body>
</html>"""


# ---------------------------------------------------------------------------
# Small building blocks
# ---------------------------------------------------------------------------
def initials(name: str) -> str:
    parts = [p for p in (name or "").replace(".", " ").split() if p]
    return ("".join(p[0] for p in parts[:2]) or "?").upper()


def header() -> html.Header:
    user = get_current_user() or "local dev"
    return html.Header(
        html.Div(
            [
                html.Div(
                    [
                        html.Span("Lilly", style={**t.eyebrow(t.BLUE_LIGHT), "letterSpacing": "0.32em"}),
                        html.Span(style={"width": "1px", "height": "22px", "background": "rgba(255,255,255,.18)"}),
                        html.Span(
                            "CDDA Meeting Manager",
                            style={"font": f"700 19px/1.2 {t.FONT_DISPLAY}", "letterSpacing": "-0.01em", "color": "#fff"},
                        ),
                    ],
                    style={"display": "flex", "alignItems": "center", "gap": "18px"},
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Span("Environment", style={**t.eyebrow("#A9B6CC"), "font": f"700 10px/1 {t.FONT}"}),
                                html.Span(config.ENVIRONMENT_LABEL, style={"font": f"400 13px/1 {t.FONT}", "color": "#fff"}),
                            ],
                            style={"display": "flex", "flexDirection": "column", "gap": "2px", "textAlign": "right"},
                        ),
                        html.Span(
                            initials(user),
                            title=user,
                            style={
                                "width": "34px", "height": "34px", "borderRadius": "999px",
                                "background": t.NAVY_DEEP, "border": "1px solid rgba(255,255,255,.22)",
                                "display": "flex", "alignItems": "center", "justifyContent": "center",
                                "font": f"700 12px/1 {t.FONT}", "color": "#fff",
                            },
                        ),
                    ],
                    style={"display": "flex", "alignItems": "center", "gap": "16px"},
                ),
            ],
            style=t.HEADER_INNER,
        ),
        style=t.HEADER,
    )


def banner(text: str, accent: str = t.RED) -> html.Div:
    return html.Div(text, style={**t.BANNER, "borderLeft": f"3px solid {accent}"})


def startup_banners() -> list:
    out = []
    missing = config.missing_settings()
    if missing:
        out.append(
            banner(
                "Missing configuration: " + ", ".join(missing)
                + ". Set these in Posit Connect -> Settings -> Vars, then restart the app."
            )
        )
    elif not config.SP_WRITE_ENABLED:
        out.append(
            banner(
                "Read-only mode. The service principal has read access to this "
                "SharePoint site, so adding, approving and deleting are disabled. "
                "Once write access is granted, set SP_WRITE_ENABLED=true in Posit Vars.",
                accent=t.BLUE,
            )
        )
    return out


def can_approve() -> bool:
    if not config.APPROVER_EMAILS:
        return False
    return get_current_email() in config.APPROVER_EMAILS


# ---------------------------------------------------------------------------
# Home screen
# ---------------------------------------------------------------------------
def forum_card(forum: dict, index: int) -> html.Section:
    tint = t.TINT_SKY if index % 2 == 0 else t.TINT_BLUE
    accent = t.BLUE_LIGHT if index % 2 == 0 else t.BLUE
    rule = t.BORDER_SKY if index % 2 == 0 else t.BORDER_BLUE
    instances = sp.get_instances(forum["id"])
    item_count = sum(len(sp.get_agenda_items(i["date"])) for i in instances)

    return html.Section(
        [
            html.Div(
                [
                    html.Span(f"{index + 1:02d}", style={"font": f"700 13px/1 {t.FONT_DISPLAY}", "letterSpacing": "0.08em", "color": t.BLUE}),
                    html.Span(f"{forum['duration']} minute forum", style=t.eyebrow()),
                ],
                style={"display": "flex", "alignItems": "baseline", "gap": "12px"},
            ),
            html.H2(forum["title"], style=t.H2),
            html.P(forum["description"] or "No description recorded for this forum.",
                   style={**t.BODY, "font": f"400 15px/1.6 {t.FONT}"}),
            html.Div(style={"height": "1px", "background": rule, "marginTop": "4px"}),
            html.Div(
                [
                    html.Span(
                        f"{len(instances)} meeting date{'' if len(instances) == 1 else 's'} · "
                        f"{item_count} agenda item{'' if item_count == 1 else 's'}",
                        style={"font": f"400 13px/1.4 {t.FONT}", "color": t.TEXT_MUTED},
                    ),
                    html.Button(
                        "Select",
                        id={"type": "pick-forum", "forum": forum["id"]},
                        n_clicks=0,
                        className="btn-primary",
                        style=t.BTN_PRIMARY,
                    ),
                ],
                style={"display": "flex", "alignItems": "center", "justifyContent": "space-between", "gap": "16px"},
            ),
        ],
        style={
            "background": tint, "borderRadius": "8px", "borderLeft": f"3px solid {accent}",
            "padding": "28px 28px 24px", "display": "flex", "flexDirection": "column", "gap": "16px",
        },
    )


def home_screen() -> html.Main:
    try:
        forums = sp.get_forums()
    except Exception as exc:
        log.exception("Failed to load forums")
        return html.Main(banner(f"Could not load meeting forums: {exc}"), style=t.MAIN)

    body = (
        html.Div([forum_card(f, i) for i, f in enumerate(forums)],
                 className="forum-grid", style={"marginTop": "36px"})
        if forums
        else html.Div("No forums found in the CDDAMeetings list.",
                      style={**t.BODY, "marginTop": "28px", "color": t.TEXT_MUTED})
    )

    return html.Main(
        html.Div(
            [
                html.Div(
                    [
                        html.Span("Meeting forums", style=t.eyebrow(t.BLUE)),
                        html.H1("Choose a forum to manage", style=t.H1),
                        html.P(
                            "Select a forum to review its meeting dates, add agenda items "
                            "and track the time still available in each session.",
                            style=t.BODY,
                        ),
                    ],
                    style={"display": "flex", "flexDirection": "column", "gap": "12px", "maxWidth": "620px"},
                ),
                body,
            ],
            style={**t.CARD, "padding": "44px 44px 48px"},
        ),
        style=t.MAIN,
    )


# ---------------------------------------------------------------------------
# Agenda screen
# ---------------------------------------------------------------------------
def date_row(instance: dict, forum: dict, selected: bool) -> html.Button:
    items = sp.get_agenda_items(instance["date"])
    used = sum(i["minutes"] for i in items)
    left = max(0, forum["duration"] - used)
    pct = min(100, round(used / forum["duration"] * 100)) if forum["duration"] else 0
    badge = "Open" if not items else ("Full" if left == 0 else "")

    return html.Button(
        [
            html.Span(
                [
                    html.Span(instance["date_label"], style={"font": f"700 17px/1.35 {t.FONT}", "color": t.NAVY}),
                    html.Span(badge, style={**t.eyebrow(t.TEXT_MUTED if not items else t.RED),
                                            "font": f"700 11px/1 {t.FONT}", "letterSpacing": "0.08em"}),
                ],
                style={"display": "flex", "alignItems": "center", "justifyContent": "space-between", "gap": "12px"},
            ),
            html.Span(
                f"{len(items)} agenda item{'' if len(items) == 1 else 's'} · {left} min left",
                style={"font": f"400 13px/1.3 {t.FONT}", "color": t.TEXT_MUTED},
            ),
            html.Span(
                html.Span(style={"display": "block", "height": "3px", "borderRadius": "999px",
                                 "background": t.RED if selected else t.RULE, "width": f"{pct}%"}),
                style={"display": "block", "height": "3px", "background": t.BORDER,
                       "borderRadius": "999px", "overflow": "hidden"},
            ),
        ],
        id={"type": "pick-date", "instance": instance["id"]},
        n_clicks=0,
        className="date-row",
        style={
            "width": "100%", "textAlign": "left", "border": "none",
            "borderLeft": f"3px solid {t.RED if selected else t.RULE}",
            "borderRadius": "8px", "padding": "16px 18px", "cursor": "pointer",
            "display": "flex", "flexDirection": "column", "gap": "10px",
            "background": t.TINT_BLUE if selected else t.SURFACE_ROW,
        },
    )


def agenda_row(item: dict, position: int, approver: bool) -> html.Div:
    approved = str(item["status"]).lower() == "approved"
    docs = sp.get_documents(item["id"])

    controls = [
        html.Button("Docs", id={"type": "toggle-docs", "item": item["id"]}, n_clicks=0,
                    className="btn-icon", style=t.BTN_ICON, title="Attachments"),
        html.Button("Delete", id={"type": "delete-item", "item": item["id"]}, n_clicks=0,
                    className="btn-icon", style=t.BTN_ICON, disabled=not config.SP_WRITE_ENABLED,
                    title="Remove item and its documents"),
    ]
    if approver:
        controls.append(
            html.Button(
                "Approved" if approved else "Approve",
                id={"type": "approve-item", "item": item["id"]}, n_clicks=0,
                className="btn-icon", style={
                    **t.BTN_ICON,
                    "color": t.STATUS_APPROVED if approved else t.TEXT_MUTED,
                    "borderColor": t.STATUS_APPROVED if approved else t.BORDER,
                },
                disabled=approved or not config.SP_WRITE_ENABLED,
            )
        )

    doc_panel = html.Div(
        [
            html.Div(
                [
                    html.Span(doc["title"], style={"font": f"400 14px/1.4 {t.FONT}", "color": t.TEXT}),
                    html.Button("Remove", id={"type": "delete-doc", "doc": doc["id"], "item": item["id"]},
                                n_clicks=0, className="btn-quiet", style=t.BTN_QUIET,
                                disabled=not config.SP_WRITE_ENABLED),
                ],
                style={"display": "flex", "justifyContent": "space-between", "alignItems": "center",
                       "padding": "8px 0", "borderBottom": f"1px solid {t.BORDER}"},
            )
            for doc in docs
        ]
        + ([] if docs else [
            html.Div("No documents attached.", style={"font": f"400 14px/1.4 {t.FONT}",
                                                      "color": t.TEXT_MUTED, "padding": "8px 0"})
        ])
        + [
            dcc.Upload(
                html.Span("Upload a document", style={"font": f"700 13px/1 {t.FONT}", "color": t.BLUE}),
                id={"type": "upload-doc", "item": item["id"]},
                multiple=False,
                disabled=not (config.SP_WRITE_ENABLED or config.UPLOAD_FLOW_URL),
                style={"marginTop": "10px", "padding": "12px", "border": f"1px dashed {t.RULE}",
                       "borderRadius": "6px", "textAlign": "center", "cursor": "pointer"},
            ),
        ],
        id={"type": "docs-panel", "item": item["id"]},
        style={"display": "none", "marginTop": "12px", "background": t.SURFACE_MUTED,
               "borderRadius": "8px", "padding": "12px 16px"},
    )

    return html.Div(
        [
            html.Article(
                [
                    html.Span(f"{position:02d}", style={"font": f"700 13px/1.6 {t.FONT_DISPLAY}",
                                                        "letterSpacing": "0.08em", "color": t.BLUE}),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Span(f"{item['minutes']} minutes", style=t.BADGE),
                                    html.Span(
                                        item["status"] or "Pending",
                                        style={**t.BADGE,
                                               "background": "#E7F3EC" if approved else "#FDF2E2",
                                               "color": t.STATUS_APPROVED if approved else t.STATUS_PENDING},
                                    ),
                                ],
                                style={"display": "flex", "gap": "8px"},
                            ),
                            html.H3(item["title"], style={"margin": "0", "font": f"700 17px/1.35 {t.FONT}", "color": t.NAVY}),
                            html.P(item["description"] or "No description provided.",
                                   style={"margin": "0", "font": f"400 15px/1.6 {t.FONT}",
                                          "color": t.TEXT, "maxWidth": "62ch"}),
                            html.Span(
                                [
                                    html.Span(style={"width": "6px", "height": "6px", "borderRadius": "999px",
                                                     "background": t.BLUE, "display": "inline-block"}),
                                    item["speaker"] or "To be confirmed",
                                ],
                                style={"display": "flex", "alignItems": "center", "gap": "8px",
                                       "font": f"400 13px/1.3 {t.FONT}", "color": t.TEXT_MUTED},
                            ),
                        ],
                        style={"display": "flex", "flexDirection": "column", "gap": "8px", "minWidth": "0"},
                    ),
                    html.Div(controls, style={"display": "flex", "gap": "8px"}),
                ],
                style={"display": "grid", "gridTemplateColumns": "44px 1fr auto",
                       "alignItems": "start", "gap": "20px", "padding": "24px 0"},
            ),
            doc_panel,
        ],
        style={"borderBottom": f"1px solid {t.BORDER}"},
    )


def add_form(remaining: int) -> html.Div:
    options = [o for o in config.TIME_OPTIONS if o <= remaining] or [config.TIME_OPTIONS[0]]
    return html.Div(
        [
            html.Span("New agenda item", style=t.eyebrow(t.BLUE)),
            html.Div(
                [
                    html.Label(["Topic", dcc.Input(id="draft-topic", type="text",
                                                   placeholder="Short, verb-first title",
                                                   style=t.INPUT, debounce=True)], style=t.LABEL),
                    html.Label(["Minutes", dcc.Dropdown(
                        id="draft-minutes",
                        options=[{"label": f"{o} minutes", "value": o} for o in options],
                        value=options[0], clearable=False,
                        style={"font": f"400 15px/1.3 {t.FONT}"})], style=t.LABEL),
                ],
                style={"display": "grid", "gridTemplateColumns": "1fr 200px", "gap": "16px"},
            ),
            html.Div(
                [
                    html.Label(["Description", dcc.Input(id="draft-desc", type="text",
                                                         placeholder="One or two sentences of context",
                                                         style=t.INPUT, debounce=True)], style=t.LABEL),
                    html.Label(["Presenter email", dcc.Input(id="draft-presenter", type="text",
                                                             placeholder="name@lilly.com",
                                                             style=t.INPUT, debounce=True)], style=t.LABEL),
                ],
                style={"display": "grid", "gridTemplateColumns": "1fr 200px", "gap": "16px"},
            ),
            html.Div(
                [
                    html.Button("Save item", id="save-item", n_clicks=0, className="btn-dark",
                                style=t.BTN_DARK, disabled=not config.SP_WRITE_ENABLED),
                    html.Button("Cancel", id="cancel-item", n_clicks=0, className="btn-quiet", style=t.BTN_QUIET),
                    html.Span(f"{remaining} minutes still available", id="remaining-note",
                              style={"font": f"400 13px/1 {t.FONT}", "color": t.TEXT_MUTED}),
                ],
                style={"display": "flex", "alignItems": "center", "gap": "20px", "marginTop": "4px"},
            ),
        ],
        style={"background": t.SURFACE_MUTED, "borderRadius": "8px", "borderLeft": f"3px solid {t.BLUE}",
               "padding": "24px", "marginTop": "20px", "display": "flex",
               "flexDirection": "column", "gap": "16px"},
    )


def agenda_screen(nav: dict) -> html.Main:
    try:
        forums = {f["id"]: f for f in sp.get_forums()}
        forum = forums.get(str(nav.get("forum_id")))
        if forum is None:
            return html.Main(banner("That forum is no longer available."), style=t.MAIN)

        instances = sp.get_instances(forum["id"])
        if not instances:
            return html.Main(
                html.Div([html.H1(forum["title"], style=t.H1),
                          banner("This forum has no meeting dates in MeetingInstances yet.", accent=t.BLUE)],
                         style={**t.CARD, "padding": "36px"}),
                style=t.MAIN,
            )

        selected = next((i for i in instances if i["id"] == str(nav.get("instance_id"))), instances[0])
        items = sp.get_agenda_items(selected["date"])
        used = sum(i["minutes"] for i in items)
        remaining = max(0, forum["duration"] - used)
        approver = can_approve()
    except Exception as exc:
        log.exception("Failed to render agenda screen")
        return html.Main(banner(f"Could not load this forum: {exc}"), style=t.MAIN)

    rail = html.Aside(
        [
            html.Div(
                [
                    html.Span("Meeting dates", style=t.eyebrow()),
                    html.Span(f"{len(instances)} scheduled",
                              style={"font": f"400 12px/1 {t.FONT}", "color": t.TEXT_FAINT}),
                ],
                style={"display": "flex", "alignItems": "baseline", "justifyContent": "space-between",
                       "gap": "12px", "marginBottom": "16px"},
            ),
            html.Div([date_row(i, forum, i["id"] == selected["id"]) for i in instances],
                     style={"display": "flex", "flexDirection": "column", "gap": "8px"}),
        ],
        style={"borderRight": f"1px solid {t.BORDER}", "padding": "28px 24px 32px", "minHeight": "560px"},
    )

    detail = html.Section(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.Span("Agenda items", style=t.eyebrow()),
                            html.H2(selected["date_label"], style=t.H2),
                        ],
                        style={"display": "flex", "flexDirection": "column", "gap": "6px"},
                    ),
                    html.Div(
                        [
                            html.Span(f"{used} of {forum['duration']} minutes planned · {remaining} min left",
                                      style={"font": f"400 14px/1.4 {t.FONT}", "color": t.TEXT_MUTED}),
                            html.Button("Add item", id="start-add", n_clicks=0, className="btn-primary",
                                        style={**t.BTN_PRIMARY, "padding": "12px 22px"},
                                        disabled=not config.SP_WRITE_ENABLED or remaining <= 0),
                        ],
                        style={"display": "flex", "alignItems": "center", "gap": "20px", "flexWrap": "wrap"},
                    ),
                ],
                style={"display": "flex", "alignItems": "center", "justifyContent": "space-between",
                       "gap": "20px", "flexWrap": "wrap", "paddingBottom": "16px",
                       "borderBottom": f"3px solid {t.NAVY}"},
            ),
            html.Div(id="add-form-slot"),
            html.Div([agenda_row(item, n + 1, approver) for n, item in enumerate(items)],
                     style={"display": "flex", "flexDirection": "column"}),
            html.Div(
                [
                    html.Span("No agenda items yet", style={"font": f"700 17px/1.35 {t.FONT}", "color": t.NAVY}),
                    html.P(f"This session has its full {forum['duration']} minutes available. "
                           "Add the first item to start building the agenda.",
                           style={"margin": "0", "font": f"400 15px/1.6 {t.FONT}", "color": t.TEXT, "maxWidth": "48ch"}),
                ],
                style={"marginTop": "24px", "background": t.SURFACE_MUTED, "borderRadius": "8px",
                       "borderLeft": f"3px solid {t.BLUE_LIGHT}", "padding": "32px",
                       "display": "flex" if not items else "none", "flexDirection": "column", "gap": "10px"},
            ),
        ],
        style={"padding": "28px 36px 36px", "minWidth": "0"},
    )

    return html.Main(
        html.Div(
            [
                html.Div(
                    [
                        html.Div(
                            [
                                html.Button("← All forums", id="go-home", n_clicks=0, className="btn-quiet",
                                            style={**t.BTN_QUIET, **t.eyebrow(t.BLUE)}),
                                html.H1(forum["title"], style={**t.H1, "font": f"700 28px/1.2 {t.FONT_DISPLAY}"}),
                            ],
                            style={"display": "flex", "flexDirection": "column", "gap": "10px"},
                        ),
                        html.Div(
                            [
                                html.Label("Select a meeting date", style=t.eyebrow()),
                                dcc.Dropdown(
                                    id="date-dropdown",
                                    options=[{"label": i["display_text"] or i["date_label"], "value": i["id"]}
                                             for i in instances],
                                    value=selected["id"], clearable=False,
                                    style={"font": f"700 15px/1 {t.FONT}"},
                                ),
                            ],
                            style={"display": "flex", "flexDirection": "column", "gap": "8px", "minWidth": "260px"},
                        ),
                    ],
                    style={"padding": "28px 36px 24px", "borderBottom": f"1px solid {t.BORDER}",
                           "display": "flex", "alignItems": "flex-end", "justifyContent": "space-between",
                           "gap": "28px", "flexWrap": "wrap"},
                ),
                html.Div([rail, detail], className="agenda-split"),
            ],
            style=t.CARD,
        ),
        style=t.MAIN,
    )


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
def serve_layout() -> html.Div:
    return html.Div(
        [
            dcc.Store(id="nav", data={"screen": "home", "forum_id": None, "instance_id": None}),
            dcc.Store(id="adding", data=False),
            dcc.Store(id="refresh", data=0),
            header(),
            html.Div(id="banners", children=startup_banners()),
            html.Div(id="toast"),
            html.Div(id="screen"),
        ],
        style=t.PAGE,
    )


app.layout = serve_layout


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------
@app.callback(
    Output("screen", "children"),
    Input("nav", "data"),
    Input("refresh", "data"),
)
def render_screen(nav, _refresh):
    nav = nav or {}
    if nav.get("screen") == "agenda" and nav.get("forum_id"):
        return agenda_screen(nav)
    return home_screen()


@app.callback(
    Output("nav", "data"),
    Input({"type": "pick-forum", "forum": ALL}, "n_clicks"),
    Input({"type": "pick-date", "instance": ALL}, "n_clicks"),
    Input("date-dropdown", "value"),
    Input("go-home", "n_clicks"),
    State("nav", "data"),
    prevent_initial_call=True,
)
def navigate(_forum_clicks, _date_clicks, dropdown_value, _home_clicks, nav):
    nav = dict(nav or {})
    trigger = dash.callback_context.triggered_id

    if trigger == "go-home":
        return {"screen": "home", "forum_id": None, "instance_id": None}

    if trigger == "date-dropdown":
        # The dropdown is rebuilt on every render and fires with its current
        # value; without this guard that would bounce nav -> render -> nav.
        if not dropdown_value or dropdown_value == nav.get("instance_id"):
            return no_update
        nav["instance_id"] = dropdown_value
        return nav

    if isinstance(trigger, dict):
        if trigger.get("type") == "pick-forum":
            return {"screen": "agenda", "forum_id": trigger["forum"], "instance_id": None}
        if trigger.get("type") == "pick-date":
            if trigger["instance"] == nav.get("instance_id"):
                return no_update
            nav["instance_id"] = trigger["instance"]
            return nav

    return no_update


@app.callback(
    Output("add-form-slot", "children"),
    Input("start-add", "n_clicks"),
    Input("cancel-item", "n_clicks"),
    Input("nav", "data"),
    prevent_initial_call=True,
)
def toggle_add_form(_start, _cancel, nav):
    trigger = dash.callback_context.triggered_id
    if trigger != "start-add":
        return None
    try:
        forum = next((f for f in sp.get_forums() if f["id"] == str(nav.get("forum_id"))), None)
        instances = sp.get_instances(nav.get("forum_id")) if forum else []
        selected = next((i for i in instances if i["id"] == str(nav.get("instance_id"))), instances[0] if instances else None)
        if not forum or not selected:
            return None
        remaining = max(0, forum["duration"] - sp.minutes_used(selected["date"]))
    except Exception:
        log.exception("Could not open the add form")
        return banner("Could not open the add form - check the Logs tab for the traceback.")
    return add_form(remaining)


@app.callback(
    Output("refresh", "data"),
    Output("toast", "children"),
    Output("add-form-slot", "children", allow_duplicate=True),
    Input("save-item", "n_clicks"),
    Input({"type": "delete-item", "item": ALL}, "n_clicks"),
    Input({"type": "approve-item", "item": ALL}, "n_clicks"),
    Input({"type": "delete-doc", "doc": ALL, "item": ALL}, "n_clicks"),
    Input({"type": "upload-doc", "item": ALL}, "contents"),
    State({"type": "upload-doc", "item": ALL}, "filename"),
    State("draft-topic", "value"),
    State("draft-desc", "value"),
    State("draft-minutes", "value"),
    State("draft-presenter", "value"),
    State("nav", "data"),
    State("refresh", "data"),
    prevent_initial_call=True,
)
def mutate(_save, _del, _approve, _deldoc, upload_contents, upload_names,
           topic, desc, minutes, presenter, nav, refresh):
    ctx = dash.callback_context
    trigger = ctx.triggered_id
    if trigger is None:
        return no_update, no_update, no_update

    # Newly rendered buttons arrive with n_clicks=0 and can fire this callback.
    # Only act on a real click (or a real upload payload).
    triggered_value = ctx.triggered[0]["value"] if ctx.triggered else None
    if not triggered_value:
        return no_update, no_update, no_update

    try:
        if trigger == "save-item":
            if not (topic or "").strip():
                return no_update, banner("Give the agenda item a topic before saving.", accent=t.BLUE), no_update

            forum = next((f for f in sp.get_forums() if f["id"] == str(nav.get("forum_id"))), None)
            instances = sp.get_instances(nav.get("forum_id"))
            selected = next((i for i in instances if i["id"] == str(nav.get("instance_id"))), instances[0])
            remaining = max(0, forum["duration"] - sp.minutes_used(selected["date"]))
            minutes = int(minutes or 0)
            if minutes > remaining:
                return no_update, banner(
                    f"Only {remaining} minutes remain on {selected['date_label']}."), no_update

            speaker_id = sp.resolve_site_user_id((presenter or "").strip()) if presenter else None
            sp.add_agenda_item(
                title=topic.strip(),
                description=(desc or "").strip(),
                minutes=minutes,
                meeting_date=selected["date"],
                meeting_text=forum["title"],
                speaker_lookup_id=speaker_id,
            )
            note = "" if speaker_id or not presenter else " (presenter could not be matched to a site user)"
            return (refresh or 0) + 1, banner(f"Agenda item added.{note}", accent=t.BLUE), None

        if isinstance(trigger, dict):
            kind = trigger.get("type")

            if kind == "delete-item":
                sp.delete_agenda_item(trigger["item"])
                return (refresh or 0) + 1, banner("Agenda item and its documents removed.", accent=t.BLUE), no_update

            if kind == "approve-item":
                if not can_approve():
                    return no_update, banner("You are not on the approver list for this app."), no_update
                sp.approve_agenda_item(trigger["item"])
                return (refresh or 0) + 1, banner("Agenda item approved.", accent=t.BLUE), no_update

            if kind == "delete-doc":
                sp.delete_item(config.LIST_DOCUMENTS, trigger["doc"])
                return (refresh or 0) + 1, banner("Document removed.", accent=t.BLUE), no_update

            if kind == "upload-doc":
                contents = next((c for c in (upload_contents or []) if c), None)
                filename = next((n for n in (upload_names or []) if n), "upload.bin")
                if not contents:
                    return no_update, no_update, no_update
                _, _, payload = contents.partition(",")
                sp.upload_document(
                    agenda_item_id=trigger["item"],
                    filename=filename,
                    content=base64.b64decode(payload),
                )
                return (refresh or 0) + 1, banner(f"Uploaded {filename}.", accent=t.BLUE), no_update

    except sp.ReadOnlyError as exc:
        return no_update, banner(str(exc)), no_update
    except Exception as exc:
        log.exception("Write failed")
        return no_update, banner(f"That did not save: {exc}"), no_update

    return no_update, no_update, no_update


@app.callback(
    Output({"type": "docs-panel", "item": dash.MATCH}, "style"),
    Input({"type": "toggle-docs", "item": dash.MATCH}, "n_clicks"),
    State({"type": "docs-panel", "item": dash.MATCH}, "style"),
    prevent_initial_call=True,
)
def toggle_docs(n_clicks, style):
    style = dict(style or {})
    style["display"] = "block" if (n_clicks or 0) % 2 == 1 else "none"
    return style


@server.route("/health")
def health():  # simple probe; also useful when checking Vars after a deploy
    status = sp.health()
    return (status, 200) if status.get("ok") else (status, 503)


# Gunicorn imports `server` and never runs this block - it is for local dev only.
if __name__ == "__main__":
    app.run(debug=True, port=8050)
