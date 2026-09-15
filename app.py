"""
CDDA Meeting Manager — Flask Application.
Deployed on Posit Connect as python-api.

Entrypoint: app:server

Serves a self-contained SPA from the root route.  All /api/* routes
talk to Fabric Lakehouse via the deltalake library.
"""

import json
import os
from flask import Flask, jsonify, request, make_response

import config
from fabric_graph import get_data_layer

# ============================================================================
# Flask App
# ============================================================================

server = Flask(__name__)

# ============================================================================
# HTML SPA — served from root
# ============================================================================

_HTML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")


@server.route("/")
def index():
    """Serve the SPA."""
    try:
        with open(_HTML_PATH, "r", encoding="utf-8") as f:
            return f.read(), 200, {"Content-Type": "text/html; charset=utf-8"}
    except FileNotFoundError:
        return "index.html not found", 404


# ============================================================================
# API routes — read/write Fabric Lakehouse
# ============================================================================

@server.route("/api/ping")
def api_ping():
    """Diagnostic endpoint."""
    return jsonify({
        "ok": True,
        "mode": "demo" if config.DEMO_MODE else "live",
        "workspace": config.FABRIC_WORKSPACE_ID[:8] + "..." if config.FABRIC_WORKSPACE_ID else "EMPTY",
        "lakehouse": config.FABRIC_LAKEHOUSE_ID[:8] + "..." if config.FABRIC_LAKEHOUSE_ID else "EMPTY",
    })


@server.route("/api/forums")
def api_forums():
    """Return all meeting forums from Lakehouse."""
    try:
        dl = get_data_layer()
        meetings = dl.get_meetings()
        print(f"[api] get_meetings returned {len(meetings)} rows", flush=True)
        forums = []
        for m in meetings:
            items = dl.get_agenda_items(m.get("id", ""))
            forums.append({
                "id": m.get("id", ""),
                "title": m.get("title", ""),
                "desc": m.get("description", ""),
                "forum": m.get("forum", ""),
                "duration": m.get("duration", 60),
                "itemCount": len(items),
            })
        return jsonify({"ok": True, "forums": forums})
    except Exception as exc:
        print(f"[api] /api/forums ERROR: {type(exc).__name__}: {exc}", flush=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@server.route("/api/forums/<forum_id>/items")
def api_forum_items(forum_id):
    """Return agenda items for a forum."""
    try:
        dl = get_data_layer()
        items = dl.get_agenda_items(forum_id)
        # ensure all values are JSON-serializable
        clean = []
        for it in items:
            clean.append({
                k: (str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v)
                for k, v in it.items()
            })
        return jsonify({"ok": True, "items": clean})
    except Exception as exc:
        print(f"[api] /api/forums/{forum_id}/items ERROR: {exc}", flush=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@server.route("/api/items", methods=["POST"])
def api_add_item():
    """Add an agenda item to the Lakehouse."""
    try:
        body = request.get_json(force=True)
        dl = get_data_layer()
        item_id = dl.create_agenda_item(
            meeting_id=body.get("meeting_id", ""),
            title=body.get("topic", "Untitled"),
            topic=body.get("desc", ""),
            duration=int(body.get("duration", 15)),
            presenter=body.get("presenter", ""),
        )
        if item_id:
            return jsonify({"ok": True, "id": item_id})
        return jsonify({"ok": False, "error": "Failed to create"}), 500
    except Exception as exc:
        print(f"[api] POST /api/items ERROR: {exc}", flush=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@server.route("/api/items/<item_id>", methods=["DELETE"])
def api_delete_item(item_id):
    """Delete an agenda item from the Lakehouse."""
    try:
        dl = get_data_layer()
        ok = dl.delete_agenda_item(item_id)
        return jsonify({"ok": ok})
    except Exception as exc:
        print(f"[api] DELETE /api/items/{item_id} ERROR: {exc}", flush=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@server.route("/health")
def health_check():
    return jsonify({
        "status": "ok",
        "app": "CDDA Meeting Manager",
        "mode": "demo" if config.DEMO_MODE else "live",
        "environment": config.APP_ENVIRONMENT,
    })


# ============================================================================
# Local dev
# ============================================================================

if __name__ == "__main__":
    server.run(debug=True, port=8050)
