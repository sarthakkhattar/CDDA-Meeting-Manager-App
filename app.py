"""
CDDA Meeting Manager — Dash Application.
Deployed on Posit Connect as python-dash.

Entrypoint: app:server

The UI is a self-contained SPA embedded via app.index_string.
Dash is used only as the WSGI host; the entire front-end is
vanilla HTML / CSS / JS that calls Flask API routes for data.
"""

import json
import dash
from dash import html, dcc
from flask import Blueprint, jsonify, request as flask_request

import config
from fabric_graph import get_data_layer

# ============================================================================
# Flask API Blueprint — registered BEFORE Dash to avoid route conflicts
# ============================================================================

api_bp = Blueprint("api", __name__)


@api_bp.route("/api/forums")
def api_forums():
    """Return all meeting forums."""
    try:
        dl = get_data_layer()
        meetings = dl.get_meetings()
        forums = []
        for m in meetings:
            items = dl.get_agenda_items(m["id"])
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
        print(f"[api] /api/forums error: {exc}", flush=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@api_bp.route("/api/forums/<forum_id>/items")
def api_forum_items(forum_id):
    """Return all agenda items for a forum."""
    try:
        dl = get_data_layer()
        items = dl.get_agenda_items(forum_id)
        return jsonify({"ok": True, "items": items})
    except Exception as exc:
        print(f"[api] /api/forums/{forum_id}/items error: {exc}", flush=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@api_bp.route("/api/items", methods=["POST"])
def api_add_item():
    """Add an agenda item."""
    try:
        body = flask_request.get_json(force=True)
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
        print(f"[api] POST /api/items error: {exc}", flush=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@api_bp.route("/api/items/<item_id>", methods=["DELETE"])
def api_delete_item(item_id):
    """Delete an agenda item."""
    try:
        dl = get_data_layer()
        ok = dl.delete_agenda_item(item_id)
        return jsonify({"ok": ok})
    except Exception as exc:
        print(f"[api] DELETE /api/items/{item_id} error: {exc}", flush=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@api_bp.route("/health")
def health_check():
    return (
        json.dumps({
            "status": "ok",
            "app": "CDDA Meeting Manager",
            "mode": "demo" if config.DEMO_MODE else "live",
            "environment": config.APP_ENVIRONMENT,
        }),
        200,
        {"Content-Type": "application/json"},
    )


# ============================================================================
# Dash App — we only need Dash as the WSGI wrapper for Posit Connect
# ============================================================================

app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True,
    title="CDDA Meeting Manager",
    use_pages=False,
    pages_folder="",
)
server = app.server  # Required for Posit Connect entrypoint app:server

# Register API blueprint on the Flask server
server.register_blueprint(api_bp)


# ============================================================================
# Complete SPA embedded as Dash index_string
# ============================================================================

app.index_string = r'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CDDA Meeting Manager</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{
            font-family:'Segoe UI',-apple-system,BlinkMacSystemFont,Roboto,Helvetica,Arial,sans-serif;
            background:#f2f4f7;color:#3a4658;
        }

        /* ── Header ─────────────────────────────────────────────── */
        .hdr{background:#0b1d3a;color:#fff;display:flex;align-items:center;height:56px;border-bottom:3px solid #e4202d;padding:0 24px}
        .hdr-logo{font-weight:700;font-size:20px;letter-spacing:.5px}
        .hdr-sep{width:1px;height:28px;background:rgba(255,255,255,.25);margin:0 16px}
        .hdr-title{font-size:15px;font-weight:400;opacity:.9}

        /* ── Container ──────────────────────────────────────────── */
        .wrap{max-width:1400px;margin:0 auto;padding:24px}

        /* ── Screens ────────────────────────────────────────────── */
        .scr{display:none}.scr.on{display:block}

        /* ── Home ───────────────────────────────────────────────── */
        .home-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:24px}
        .forum-card{background:#fff;border-radius:8px;padding:24px;box-shadow:0 1px 3px rgba(0,0,0,.1);cursor:pointer;transition:.2s;border-left:4px solid #1e4ebc}
        .forum-card:hover{box-shadow:0 4px 12px rgba(0,0,0,.13);transform:translateY(-2px)}
        .forum-card h2{font-size:18px;font-weight:700;color:#0b1d3a;margin-bottom:8px}
        .forum-card p{font-size:14px;color:#6b7789;margin-bottom:16px}
        .forum-badge{font-size:22px;font-weight:700;color:#1e4ebc;background:#e8eefb;display:inline-block;padding:6px 14px;border-radius:4px}

        /* ── Agenda layout ──────────────────────────────────────── */
        .ag{display:flex;gap:20px;height:calc(100vh - 112px)}

        /* sidebar */
        .sb{width:260px;min-width:260px;background:#fff;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.1);display:flex;flex-direction:column;overflow:hidden}
        .sb-back{padding:10px 16px;display:flex;align-items:center;gap:6px;cursor:pointer;color:#1e4ebc;font-size:13px;background:#f2f4f7;border:none;width:100%;text-align:left;font-family:inherit}
        .sb-back:hover{background:#e9ecf1}
        .sb-hdr{padding:12px 16px;border-bottom:1px solid #e4e8ef;font-weight:700;font-size:14px;color:#0b1d3a}
        .sb-list{flex:1;overflow-y:auto;padding:6px 8px}
        .sb-item{padding:10px 12px;margin:3px 0;border-radius:4px;cursor:pointer;border-left:3px solid transparent;background:#f9fafb;transition:.15s}
        .sb-item:hover{background:#edf0f4}
        .sb-item.on{background:#e8eefb;border-left-color:#1e4ebc}
        .sb-date{font-size:13px;font-weight:600;color:#0b1d3a}
        .sb-cnt{font-size:12px;color:#8a95a6;margin-top:2px}

        /* main panel */
        .mn{flex:1;background:#fff;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.1);display:flex;flex-direction:column;overflow:hidden}
        .mn-hdr{padding:20px 24px;border-bottom:1px solid #e4e8ef;display:flex;justify-content:space-between;align-items:center}
        .mn-hdr h1{font-size:22px;font-weight:700;color:#0b1d3a}
        .mn-body{flex:1;overflow-y:auto;padding:20px 24px}

        /* ── Buttons ────────────────────────────────────────────── */
        .btn{padding:8px 16px;border-radius:4px;border:none;cursor:pointer;font-family:inherit;font-size:13px;font-weight:500;transition:.15s}
        .btn-p{background:#1e4ebc;color:#fff}.btn-p:hover{background:#163d99}
        .btn-s{background:#e9ecf1;color:#0b1d3a;border:1px solid #d0d5df}.btn-s:hover{background:#d8dce4}
        .btn-d{background:#fbe8e8;color:#c4141f;font-size:12px;padding:5px 10px;border-radius:3px}.btn-d:hover{background:#f2d0d0}

        /* ── Time budget ────────────────────────────────────────── */
        .tb{margin-bottom:20px;padding:14px 16px;background:#f9fafb;border-radius:6px}
        .tb-row{display:flex;justify-content:space-between;font-size:13px;color:#6b7789;margin-bottom:6px;font-weight:600}
        .tb-bar{width:100%;height:8px;background:#e4e8ef;border-radius:4px;overflow:hidden}
        .tb-fill{height:100%;border-radius:4px;transition:width .3s}

        /* ── Agenda items ───────────────────────────────────────── */
        .items{display:flex;flex-direction:column;gap:10px}
        .ag-item{background:#f9fafb;border:1px solid #e4e8ef;border-radius:6px;padding:14px 16px;display:flex;justify-content:space-between;align-items:flex-start}
        .it-topic{font-weight:700;color:#0b1d3a;font-size:14px;margin-bottom:3px}
        .it-pres{font-size:13px;color:#6b7789;margin-bottom:3px}
        .it-desc{font-size:13px;color:#3a4658;line-height:1.4;margin-bottom:6px}
        .it-dur{background:#e8eefb;color:#1e4ebc;padding:2px 8px;border-radius:3px;font-size:12px;font-weight:500;display:inline-block}
        .empty{text-align:center;padding:40px 24px;color:#8a95a6}

        /* ── Add form ───────────────────────────────────────────── */
        .add-form{background:#f9fafb;border:1px dashed #1e4ebc;border-radius:6px;padding:16px;margin-top:14px}
        .add-form.hid{display:none}
        .fg{margin-bottom:10px}
        .fg label{display:block;font-size:13px;font-weight:600;color:#3a4658;margin-bottom:3px}
        .fg input,.fg select,.fg textarea{width:100%;padding:8px 10px;border:1px solid #d0d5df;border-radius:4px;font-family:inherit;font-size:13px;color:#3a4658}
        .fg textarea{resize:vertical;min-height:56px}
        .frow{display:grid;grid-template-columns:1fr 1fr;gap:12px}
        .fact{display:flex;gap:8px;justify-content:flex-end;margin-top:10px}

        /* ── Loading ────────────────────────────────────────────── */
        .loading{text-align:center;padding:40px;color:#8a95a6}

        /* ── Responsive ─────────────────────────────────────────── */
        @media(max-width:900px){
            .ag{flex-direction:column;height:auto}
            .sb{width:100%;min-width:0;max-height:260px}
            .mn{min-height:420px}
            .frow{grid-template-columns:1fr}
        }
    </style>
</head>
<body>

<!-- Header -->
<div class="hdr">
    <span class="hdr-logo">Lilly</span>
    <span class="hdr-sep"></span>
    <span class="hdr-title">CDDA Meeting Manager</span>
</div>

<div class="wrap">

    <!-- ═══ Home screen ═══ -->
    <div id="scrHome" class="scr on">
        <div class="home-grid" id="forumGrid">
            <div class="loading">Loading forums...</div>
        </div>
    </div>

    <!-- ═══ Agenda screen ═══ -->
    <div id="scrAgenda" class="scr">
        <div class="ag">

            <!-- sidebar -->
            <div class="sb">
                <button class="sb-back" onclick="MM.goHome()">&#8592; Back to Forums</button>
                <div class="sb-hdr" id="sbTitle"></div>
                <div class="sb-list" id="sbList"></div>
            </div>

            <!-- main -->
            <div class="mn">
                <div class="mn-hdr">
                    <h1 id="mnDate"></h1>
                    <button class="btn btn-p" onclick="MM.toggleForm()">+ Add Item</button>
                </div>
                <div class="mn-body">
                    <div class="tb" id="timeBudget">
                        <div class="tb-row"><span>Time Budget</span><span id="tbText"></span></div>
                        <div class="tb-bar"><div class="tb-fill" id="tbFill"></div></div>
                    </div>
                    <div class="items" id="agItems"></div>

                    <!-- add-item form -->
                    <div class="add-form hid" id="addForm">
                        <div class="fg"><label>Topic</label><input id="fTopic" placeholder="Enter topic name"></div>
                        <div class="frow">
                            <div class="fg"><label>Duration (minutes)</label>
                                <select id="fDur">
                                    <option value="5">5 minutes</option>
                                    <option value="10">10 minutes</option>
                                    <option value="15" selected>15 minutes</option>
                                    <option value="20">20 minutes</option>
                                    <option value="30">30 minutes</option>
                                    <option value="45">45 minutes</option>
                                    <option value="60">60 minutes</option>
                                </select>
                            </div>
                            <div class="fg"><label>Presenter</label><input id="fPres" placeholder="Presenter name"></div>
                        </div>
                        <div class="fg"><label>Description</label><textarea id="fDesc" placeholder="Optional description"></textarea></div>
                        <div class="fact">
                            <button class="btn btn-s" onclick="MM.toggleForm()">Cancel</button>
                            <button class="btn btn-p" onclick="MM.addItem()">Add to Agenda</button>
                        </div>
                    </div>
                </div>
            </div>

        </div>
    </div>
</div>

<!-- Dash renderer placeholder (required by Dash but invisible) -->
<div id="_dash-app-content" style="display:none">{%app_entry%}</div>
<footer style="display:none">{%config%}{%scripts%}{%renderer%}</footer>

<script>
// ======================================================================
// CDDA Meeting Manager — fetches data from Flask API → Fabric Lakehouse
// ======================================================================
const MM = (() => {
    const CAP = 60;   // minutes per meeting

    let forums  = [];  // loaded from API
    let items   = [];  // agenda items for current forum
    let curForum = null;

    // ── API helpers ─────────────────────────────────────────
    const BASE = window.location.pathname.replace(/\/$/, '');
    function api(path, opts) {
        return fetch(BASE + path, opts).then(r => r.json());
    }

    // ── Load forums from Lakehouse ──────────────────────────
    async function loadForums() {
        try {
            const res = await api('/api/forums');
            if (res.ok) {
                forums = res.forums;
            } else {
                console.error('API error:', res.error);
                forums = [];
            }
        } catch (e) {
            console.error('Fetch error:', e);
            forums = [];
        }
        renderHome();
    }

    // ── Load agenda items for a forum ───────────────────────
    async function loadItems(forumId) {
        try {
            const res = await api('/api/forums/' + forumId + '/items');
            if (res.ok) {
                items = res.items;
            } else {
                console.error('API error:', res.error);
                items = [];
            }
        } catch (e) {
            console.error('Fetch error:', e);
            items = [];
        }
    }

    // ── Navigation ───────────────────────────────────────────
    function goHome() {
        curForum = null;
        items = [];
        el('scrHome').classList.add('on');
        el('scrAgenda').classList.remove('on');
        loadForums();
    }

    async function openForum(fid) {
        curForum = forums.find(f => f.id === fid);
        if (!curForum) return;
        el('scrHome').classList.remove('on');
        el('scrAgenda').classList.add('on');
        await loadItems(fid);
        renderSidebar();
        renderMain();
    }

    // ── Render: home ─────────────────────────────────────────
    function renderHome() {
        const g = el('forumGrid');
        g.innerHTML = '';
        if (!forums.length) {
            g.innerHTML = '<div class="empty">No forums found. Check Lakehouse connection.</div>';
            return;
        }
        for (const f of forums) {
            const c = document.createElement('div');
            c.className = 'forum-card';
            c.onclick = () => openForum(f.id);
            c.innerHTML =
                '<h2>' + esc(f.title) + '</h2>' +
                '<p>'  + esc(f.desc)  + '</p>' +
                '<span class="forum-badge">' + f.itemCount + ' item' + (f.itemCount !== 1 ? 's' : '') + '</span>';
            g.appendChild(c);
        }
    }

    // ── Render: sidebar ──────────────────────────────────────
    function renderSidebar() {
        el('sbTitle').textContent = curForum ? curForum.title : '';
        const list = el('sbList');
        list.innerHTML = '<div style="padding:12px;color:#8a95a6;font-size:13px">All agenda items shown below</div>';
    }

    // ── Render: main panel ───────────────────────────────────
    function renderMain() {
        const cap = curForum ? curForum.duration : CAP;
        el('mnDate').textContent = curForum ? curForum.title : '';

        // time budget
        const used = items.reduce((s, i) => s + (i.duration || 0), 0);
        const pct  = cap > 0 ? Math.min(Math.round(used / cap * 100), 100) : 0;
        el('tbText').textContent = used + ' / ' + cap + ' minutes';
        const fill = el('tbFill');
        fill.style.width = pct + '%';
        fill.style.background = pct > 90 ? '#e4202d' : pct > 75 ? '#f0ad4e' : '#1e4ebc';

        // items
        const box = el('agItems');
        box.innerHTML = '';
        if (!items.length) {
            box.innerHTML = '<div class="empty">No agenda items yet. Click "+ Add Item" to get started.</div>';
            return;
        }
        for (const it of items) {
            const row = document.createElement('div');
            row.className = 'ag-item';
            row.innerHTML =
                '<div style="flex:1">' +
                    '<div class="it-topic">' + esc(it.title || it.topic || '') + '</div>' +
                    (it.presenter ? '<div class="it-pres">Presenter: ' + esc(it.presenter) + '</div>' : '') +
                    (it.topic     ? '<div class="it-desc">' + esc(it.topic) + '</div>' : '') +
                    '<span class="it-dur">' + (it.duration || 0) + ' min</span>' +
                '</div>' +
                '<button class="btn btn-d" data-rm="' + it.id + '">Remove</button>';
            box.appendChild(row);
        }
        box.querySelectorAll('[data-rm]').forEach(b =>
            b.addEventListener('click', () => removeItem(b.dataset.rm)));
    }

    // ── Add / remove ─────────────────────────────────────────
    function toggleForm() {
        el('addForm').classList.toggle('hid');
        if (!el('addForm').classList.contains('hid')) el('fTopic').focus();
    }

    async function addItem() {
        const topic = el('fTopic').value.trim();
        if (!topic) { alert('Please enter a topic'); return; }
        const dur  = parseInt(el('fDur').value, 10);
        const pres = el('fPres').value.trim();
        const desc = el('fDesc').value.trim();

        try {
            const res = await api('/api/items', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    meeting_id: curForum.id,
                    topic: topic,
                    duration: dur,
                    presenter: pres,
                    desc: desc
                })
            });
            if (!res.ok) { alert('Error: ' + (res.error || 'Failed to add')); return; }
        } catch (e) {
            alert('Network error: ' + e.message);
            return;
        }

        // clear form and reload
        el('fTopic').value = ''; el('fDur').value = '15'; el('fPres').value = ''; el('fDesc').value = '';
        toggleForm();
        await loadItems(curForum.id);
        renderSidebar();
        renderMain();
    }

    async function removeItem(iid) {
        if (!confirm('Remove this item?')) return;
        try {
            await api('/api/items/' + iid, { method: 'DELETE' });
        } catch (e) {
            alert('Error: ' + e.message);
        }
        await loadItems(curForum.id);
        renderSidebar();
        renderMain();
    }

    // ── Helpers ──────────────────────────────────────────────
    function el(id) { return document.getElementById(id); }
    function esc(s) { const d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML; }

    // ── Boot ─────────────────────────────────────────────────
    document.addEventListener('DOMContentLoaded', loadForums);

    return { goHome, openForum, toggleForm, addItem, removeItem };
})();
</script>
</body>
</html>
'''

# Minimal Dash layout — required by Dash internals but not visible
app.layout = html.Div(id="hidden-dash-root", style={"display": "none"})


# ============================================================================
# Local dev
# ============================================================================

if __name__ == "__main__":
    app.run(debug=True, port=8050)
