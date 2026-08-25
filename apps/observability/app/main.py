import html, json, os, sqlite3, time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

HERE=Path(__file__).resolve().parent.parent
DB=Path(os.getenv('OBSERVABILITY_STORE_PATH',str(HERE/'data'/'observability.db'))); DB.parent.mkdir(parents=True,exist_ok=True)
API_KEY=os.getenv('OBSERVABILITY_API_KEY')
LANGFUSE_ENABLED=os.getenv('LANGFUSE_ENABLED','false').lower()=='true'

class Event(BaseModel):
    event_id:str
    ts:float=Field(default_factory=time.time)
    event_type:str
    name:str
    session_id:str|None=None
    user_id:str|None=None
    request_id:str|None=None
    metadata:dict[str,Any]=Field(default_factory=dict)

def conn(): return sqlite3.connect(DB)
def init():
    with conn() as c: c.execute('CREATE TABLE IF NOT EXISTS events(event_id TEXT PRIMARY KEY,ts REAL,event_type TEXT,name TEXT,session_id TEXT,user_id TEXT,request_id TEXT,metadata_json TEXT)')
init(); app=FastAPI(title='Workforce AI Observability')

def auth(x_api_key):
    if API_KEY and x_api_key!=API_KEY: raise HTTPException(401,'Invalid observability API key')

def forward_langfuse(e:Event):
    if not LANGFUSE_ENABLED:return
    try:
        from langfuse import get_client, propagate_attributes
        lf=get_client()
        with lf.start_as_current_observation(as_type=e.event_type if e.event_type in {'span','agent','tool','chain','retriever','evaluator','guardrail','generation','embedding'} else 'span',name=e.name,input=None,metadata=e.metadata) as obs:
            with propagate_attributes(session_id=e.session_id,user_id=e.user_id): obs.update(output={'request_id':e.request_id})
        lf.flush()
    except Exception as exc:
        print('Langfuse forward failed:',exc)

@app.get('/health')
def health(): return {'status':'ok','service':'observability','langfuse_enabled':LANGFUSE_ENABLED}
@app.post('/events')
def events(e:Event,x_api_key:str|None=Header(default=None)):
    auth(x_api_key)
    # Do not persist raw prompts/document bodies here. Backend should send sanitized metadata only.
    with conn() as c:c.execute('INSERT OR REPLACE INTO events VALUES(?,?,?,?,?,?,?,?)',(e.event_id,e.ts,e.event_type,e.name,e.session_id,e.user_id,e.request_id,json.dumps(e.metadata)))
    forward_langfuse(e);return {'status':'recorded'}
@app.get('/api/events')
def recent(limit:int=100):
    with conn() as c: rows=c.execute('SELECT event_id,ts,event_type,name,session_id,user_id,request_id,metadata_json FROM events ORDER BY ts DESC LIMIT ?', (min(limit,500),)).fetchall()
    return [{'event_id':r[0],'ts':r[1],'event_type':r[2],'name':r[3],'session_id':r[4],'user_id':r[5],'request_id':r[6],'metadata':json.loads(r[7] or '{}')} for r in rows]
@app.get('/',response_class=HTMLResponse)
def dashboard():
    rows=recent(80); counts={}
    for r in rows:counts[r['event_type']]=counts.get(r['event_type'],0)+1
    cards=''.join(f'<div class="card"><b>{html.escape(k)}</b><span>{v}</span></div>' for k,v in sorted(counts.items()))
    trs=''.join(f"<tr><td>{time.strftime('%H:%M:%S',time.localtime(r['ts']))}</td><td>{html.escape(r['event_type'])}</td><td>{html.escape(r['name'])}</td><td>{html.escape(str(r.get('request_id') or ''))}</td><td><code>{html.escape(json.dumps(r['metadata']))[:220]}</code></td></tr>" for r in rows)
    return f"""<!doctype html><html><head><title>AI Observability</title><style>body{{font-family:system-ui;background:#f7f8fa;margin:30px;color:#16202a}}.cards{{display:flex;gap:10px;flex-wrap:wrap}}.card{{background:white;border:1px solid #ddd;border-radius:10px;padding:12px 18px;display:flex;gap:24px}}table{{width:100%;background:white;border-collapse:collapse;margin-top:20px}}td,th{{padding:10px;border-bottom:1px solid #eee;text-align:left;font-size:13px}}code{{font-size:11px}}</style></head><body><h1>Workforce AI Observability</h1><p>Local PoC trace collector. Langfuse forwarding: <b>{LANGFUSE_ENABLED}</b></p><div class="cards">{cards}</div><table><thead><tr><th>Time</th><th>Type</th><th>Name</th><th>Request</th><th>Metadata</th></tr></thead><tbody>{trs}</tbody></table></body></html>"""
