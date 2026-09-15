"""
CDDA Meeting Manager — Dash Application (python-dash).
Entrypoint: app:server

Data is injected server-side via interpolate_index() so no custom
Flask API routes are needed (Posit's Dash middleware blocks them).
Mutations go through Dash's _dash-update-component endpoint.
"""

import json
import dash
from dash import html, dcc, Input, Output
from dash.exceptions import PreventUpdate

import config
from fabric_graph import get_data_layer


# ============================================================================
# Helper — load all data from Fabric once per page render
# ============================================================================

def _load_all_data():
    try:
        dl = get_data_layer()
        meetings = dl.get_meetings()
        forums, all_items = [], {}
        for m in meetings:
            mid = m.get("id", "")
            items = dl.get_agenda_items(mid)
            clean = [{k: (str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v)
                       for k, v in it.items()} for it in items]
            forums.append({
                "id": mid, "title": m.get("title", ""),
                "desc": m.get("description", ""), "forum": m.get("forum", ""),
                "duration": m.get("duration", 60), "itemCount": len(items),
            })
            all_items[mid] = clean
        return forums, all_items
    except Exception as exc:
        print(f"[data] load error: {type(exc).__name__}: {exc}", flush=True)
        return [], {}


# ============================================================================
# Custom Dash — injects Lakehouse data into the HTML on every page load
# ============================================================================

class CddaDash(dash.Dash):
    def interpolate_index(self, **kwargs):
        try:
            page = super().interpolate_index(**kwargs)
            forums, all_items = _load_all_data()
            print(f"[inject] interpolate_index called — {len(forums)} forums", flush=True)
            tag = (
                "<script>"
                f"window.__FORUMS__={json.dumps(forums,default=str)};"
                f"window.__ALL_ITEMS__={json.dumps(all_items,default=str)};"
                f"window.__INJECT_OK__=true;"
                "</script>"
            )
            return page.replace("</head>", tag + "\n</head>")
        except Exception as exc:
            print(f"[inject] interpolate_index ERROR: {type(exc).__name__}: {exc}", flush=True)
            return super().interpolate_index(**kwargs)


app = CddaDash(
    __name__,
    suppress_callback_exceptions=True,
    title="CDDA Meeting Manager",
)
server = app.server  # entrypoint: app:server


# ============================================================================
# Dash callback for mutations (add / delete)
# Called from JS via POST to /_dash-update-component
# ============================================================================

@app.callback(
    Output("mutation-result", "data"),
    Input("mutation-action", "data"),
    prevent_initial_call=True,
)
def handle_mutation(action_data):
    if not action_data:
        raise PreventUpdate
    try:
        dl = get_data_layer()
        act = action_data.get("action")
        if act == "add":
            iid = dl.create_agenda_item(
                meeting_id=action_data.get("meeting_id", ""),
                title=action_data.get("topic", "Untitled"),
                topic=action_data.get("desc", ""),
                duration=int(action_data.get("duration", 15)),
                presenter=action_data.get("presenter", ""),
            )
            return {"ok": True, "id": iid}
        if act == "delete":
            dl.delete_agenda_item(action_data.get("id", ""))
            return {"ok": True}
    except Exception as exc:
        print(f"[mutation] {exc}", flush=True)
        return {"ok": False, "error": str(exc)}
    raise PreventUpdate


# ============================================================================
# Hidden Dash layout (required for the callback above)
# ============================================================================

app.layout = html.Div(
    [dcc.Store(id="mutation-action"), dcc.Store(id="mutation-result")],
    id="hidden-dash-root",
    style={"display": "none"},
)


# ============================================================================
# SPA served as index_string
# ============================================================================

app.index_string = r'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CDDA Meeting Manager</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:'Segoe UI',-apple-system,BlinkMacSystemFont,Roboto,Helvetica,Arial,sans-serif;background:#f2f4f7;color:#3a4658}
        .hdr{background:#0b1d3a;color:#fff;display:flex;align-items:center;height:56px;border-bottom:3px solid #e4202d;padding:0 24px}
        .hdr-logo{font-weight:700;font-size:20px;letter-spacing:.5px}
        .hdr-sep{width:1px;height:28px;background:rgba(255,255,255,.25);margin:0 16px}
        .hdr-title{font-size:15px;font-weight:400;opacity:.9}
        .wrap{max-width:1400px;margin:0 auto;padding:24px}
        .scr{display:none}.scr.on{display:block}
        .home-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:24px}
        .forum-card{background:#fff;border-radius:8px;padding:24px;box-shadow:0 1px 3px rgba(0,0,0,.1);cursor:pointer;transition:.2s;border-left:4px solid #1e4ebc}
        .forum-card:hover{box-shadow:0 4px 12px rgba(0,0,0,.13);transform:translateY(-2px)}
        .forum-card h2{font-size:18px;font-weight:700;color:#0b1d3a;margin-bottom:8px}
        .forum-card p{font-size:14px;color:#6b7789;margin-bottom:16px}
        .forum-badge{font-size:22px;font-weight:700;color:#1e4ebc;background:#e8eefb;display:inline-block;padding:6px 14px;border-radius:4px}
        .ag{display:flex;gap:20px;height:calc(100vh - 112px)}
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
        .mn{flex:1;background:#fff;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.1);display:flex;flex-direction:column;overflow:hidden}
        .mn-hdr{padding:20px 24px;border-bottom:1px solid #e4e8ef;display:flex;justify-content:space-between;align-items:center}
        .mn-hdr h1{font-size:22px;font-weight:700;color:#0b1d3a}
        .mn-body{flex:1;overflow-y:auto;padding:20px 24px}
        .btn{padding:8px 16px;border-radius:4px;border:none;cursor:pointer;font-family:inherit;font-size:13px;font-weight:500;transition:.15s}
        .btn-p{background:#1e4ebc;color:#fff}.btn-p:hover{background:#163d99}
        .btn-s{background:#e9ecf1;color:#0b1d3a;border:1px solid #d0d5df}.btn-s:hover{background:#d8dce4}
        .btn-d{background:#fbe8e8;color:#c4141f;font-size:12px;padding:5px 10px;border-radius:3px}.btn-d:hover{background:#f2d0d0}
        .tb{margin-bottom:20px;padding:14px 16px;background:#f9fafb;border-radius:6px}
        .tb-row{display:flex;justify-content:space-between;font-size:13px;color:#6b7789;margin-bottom:6px;font-weight:600}
        .tb-bar{width:100%;height:8px;background:#e4e8ef;border-radius:4px;overflow:hidden}
        .tb-fill{height:100%;border-radius:4px;transition:width .3s}
        .items{display:flex;flex-direction:column;gap:10px}
        .ag-item{background:#f9fafb;border:1px solid #e4e8ef;border-radius:6px;padding:14px 16px;display:flex;justify-content:space-between;align-items:flex-start}
        .it-topic{font-weight:700;color:#0b1d3a;font-size:14px;margin-bottom:3px}
        .it-pres{font-size:13px;color:#6b7789;margin-bottom:3px}
        .it-desc{font-size:13px;color:#3a4658;line-height:1.4;margin-bottom:6px}
        .it-dur{background:#e8eefb;color:#1e4ebc;padding:2px 8px;border-radius:3px;font-size:12px;font-weight:500;display:inline-block}
        .empty{text-align:center;padding:40px 24px;color:#8a95a6}
        .add-form{background:#f9fafb;border:1px dashed #1e4ebc;border-radius:6px;padding:16px;margin-top:14px}
        .add-form.hid{display:none}
        .fg{margin-bottom:10px}
        .fg label{display:block;font-size:13px;font-weight:600;color:#3a4658;margin-bottom:3px}
        .fg input,.fg select,.fg textarea{width:100%;padding:8px 10px;border:1px solid #d0d5df;border-radius:4px;font-family:inherit;font-size:13px;color:#3a4658}
        .fg textarea{resize:vertical;min-height:56px}
        .frow{display:grid;grid-template-columns:1fr 1fr;gap:12px}
        .fact{display:flex;gap:8px;justify-content:flex-end;margin-top:10px}
        @media(max-width:900px){.ag{flex-direction:column;height:auto}.sb{width:100%;min-width:0;max-height:260px}.mn{min-height:420px}.frow{grid-template-columns:1fr}}
    </style>
</head>
<body>
<div class="hdr"><span class="hdr-logo">Lilly</span><span class="hdr-sep"></span><span class="hdr-title">CDDA Meeting Manager</span></div>
<div class="wrap">
    <div id="scrHome" class="scr on"><div class="home-grid" id="forumGrid"></div></div>
    <div id="scrAgenda" class="scr"><div class="ag">
        <div class="sb">
            <button class="sb-back" onclick="MM.goHome()">&#8592; Back to Forums</button>
            <div class="sb-hdr" id="sbTitle"></div><div class="sb-list" id="sbList"></div>
        </div>
        <div class="mn">
            <div class="mn-hdr"><h1 id="mnDate"></h1><button class="btn btn-p" onclick="MM.toggleForm()">+ Add Item</button></div>
            <div class="mn-body">
                <div class="tb"><div class="tb-row"><span>Time Budget</span><span id="tbText"></span></div><div class="tb-bar"><div class="tb-fill" id="tbFill"></div></div></div>
                <div class="items" id="agItems"></div>
                <div class="add-form hid" id="addForm">
                    <div class="fg"><label>Topic</label><input id="fTopic" placeholder="Enter topic name"></div>
                    <div class="frow">
                        <div class="fg"><label>Duration</label><select id="fDur"><option value="5">5 min</option><option value="10">10 min</option><option value="15" selected>15 min</option><option value="20">20 min</option><option value="30">30 min</option><option value="45">45 min</option><option value="60">60 min</option></select></div>
                        <div class="fg"><label>Presenter</label><input id="fPres" placeholder="Presenter name"></div>
                    </div>
                    <div class="fg"><label>Description</label><textarea id="fDesc" placeholder="Optional description"></textarea></div>
                    <div class="fact"><button class="btn btn-s" onclick="MM.toggleForm()">Cancel</button><button class="btn btn-p" onclick="MM.addItem()">Add to Agenda</button></div>
                </div>
            </div>
        </div>
    </div></div>
</div>
<div id="_dash-app-content" style="display:none">{%app_entry%}</div>
<footer style="display:none">{%config%}{%scripts%}{%renderer%}</footer>
<script>
const MM=(()=>{
    const CAP=60;
    let forums=[], items=[], curForum=null;
    const BASE=window.location.pathname.replace(/\/$/,'');

    /* ── read server-injected data ─────────────────────────── */
    function loadForums(){
        forums=window.__FORUMS__||[];
        console.log('[MM] __INJECT_OK__=', window.__INJECT_OK__, 'forums=', forums.length);
        if(!forums.length && !window.__INJECT_OK__){
            el('forumGrid').innerHTML='<div class="empty">Data injection failed. Check Posit logs for [inject] messages.</div>';
            return;
        }
        renderHome();
    }
    function loadItems(fid){ items=(window.__ALL_ITEMS__||{})[fid]||[]; }

    /* ── mutations via Dash _dash-update-component ─────────── */
    async function dashMutate(payload){
        try{
            const r=await fetch(BASE+'/_dash-update-component',{
                method:'POST',
                headers:{'Content-Type':'application/json'},
                body:JSON.stringify({
                    output:'mutation-result.data',
                    outputs:{id:'mutation-result',property:'data'},
                    inputs:[{id:'mutation-action',property:'data',value:payload}],
                    changedPropIds:['mutation-action.data'],state:[]
                })
            });
            const j=await r.json();
            if(j.response) return j.response['mutation-result']?.data || j.response;
            return j;
        }catch(e){ return {ok:false,error:e.message}; }
    }

    /* ── navigation ────────────────────────────────────────── */
    function goHome(){ curForum=null;items=[];el('scrHome').classList.add('on');el('scrAgenda').classList.remove('on');renderHome(); }
    async function openForum(fid){
        curForum=forums.find(f=>f.id===fid); if(!curForum)return;
        el('scrHome').classList.remove('on');el('scrAgenda').classList.add('on');
        loadItems(fid); renderSidebar(); renderMain();
    }

    /* ── render: home ──────────────────────────────────────── */
    function renderHome(){
        const g=el('forumGrid'); g.innerHTML='';
        if(!forums.length){g.innerHTML='<div class="empty">No forums found.</div>';return;}
        for(const f of forums){
            const c=document.createElement('div');c.className='forum-card';c.onclick=()=>openForum(f.id);
            c.innerHTML='<h2>'+esc(f.title)+'</h2><p>'+esc(f.desc)+'</p><span class="forum-badge">'+f.itemCount+' item'+(f.itemCount!==1?'s':'')+'</span>';
            g.appendChild(c);
        }
    }

    /* ── render: sidebar & main ────────────────────────────── */
    function renderSidebar(){
        el('sbTitle').textContent=curForum?curForum.title:'';
        el('sbList').innerHTML='<div style="padding:12px;color:#8a95a6;font-size:13px">All agenda items below</div>';
    }
    function renderMain(){
        const cap=curForum?curForum.duration:CAP;
        el('mnDate').textContent=curForum?curForum.title:'';
        const used=items.reduce((s,i)=>s+(i.duration||0),0);
        const pct=cap>0?Math.min(Math.round(used/cap*100),100):0;
        el('tbText').textContent=used+' / '+cap+' minutes';
        const fill=el('tbFill');fill.style.width=pct+'%';
        fill.style.background=pct>90?'#e4202d':pct>75?'#f0ad4e':'#1e4ebc';
        const box=el('agItems');box.innerHTML='';
        if(!items.length){box.innerHTML='<div class="empty">No agenda items yet. Click "+ Add Item".</div>';return;}
        for(const it of items){
            const row=document.createElement('div');row.className='ag-item';
            row.innerHTML='<div style="flex:1"><div class="it-topic">'+esc(it.title||it.topic||'')+'</div>'
                +(it.presenter?'<div class="it-pres">Presenter: '+esc(it.presenter)+'</div>':'')
                +(it.topic?'<div class="it-desc">'+esc(it.topic)+'</div>':'')
                +'<span class="it-dur">'+(it.duration||0)+' min</span></div>'
                +'<button class="btn btn-d" data-rm="'+it.id+'">Remove</button>';
            box.appendChild(row);
        }
        box.querySelectorAll('[data-rm]').forEach(b=>b.addEventListener('click',()=>removeItem(b.dataset.rm)));
    }

    /* ── add / remove ──────────────────────────────────────── */
    function toggleForm(){el('addForm').classList.toggle('hid');if(!el('addForm').classList.contains('hid'))el('fTopic').focus();}

    async function addItem(){
        const topic=el('fTopic').value.trim();
        if(!topic){alert('Please enter a topic');return;}
        const res=await dashMutate({action:'add',meeting_id:curForum.id,topic,duration:parseInt(el('fDur').value,10),presenter:el('fPres').value.trim(),desc:el('fDesc').value.trim()});
        if(res&&res.ok) window.location.reload();
        else alert('Error: '+(res?.error||'Failed to add'));
    }

    async function removeItem(iid){
        if(!confirm('Remove this item?'))return;
        await dashMutate({action:'delete',id:iid});
        window.location.reload();
    }

    function el(id){return document.getElementById(id);}
    function esc(s){const d=document.createElement('div');d.textContent=s||'';return d.innerHTML;}
    document.addEventListener('DOMContentLoaded',loadForums);
    return{goHome,openForum,toggleForm,addItem,removeItem};
})();
</script>
</body>
</html>
'''

if __name__ == "__main__":
    app.run(debug=True, port=8050)
