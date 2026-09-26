from __future__ import annotations
import json, os, sqlite3, uuid, urllib.request, urllib.error
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from experience_standard import SCHEMA_VERSION, SYSTEM_PROMPT, parse_json_content, render_markdown, validate_record

ROOT = os.path.dirname(os.path.dirname(__file__))
DB = os.environ.get("EXPERIENCE_DB", os.path.join(ROOT, "data", "experience.db"))
os.makedirs(os.path.dirname(DB), exist_ok=True)

def load_local_env():
    path=os.path.join(ROOT,".env.local")
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line=line.strip()
                if not line or line.startswith("#") or "=" not in line: continue
                k,v=line.split("=",1)
                os.environ[k.strip()]=v.strip().strip('"').strip("'")
    except OSError: pass
load_local_env()

def now(): return datetime.now(timezone.utc).isoformat()
def uid(): return str(uuid.uuid4())

class Store:
    def __init__(self, path=DB):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS experiences (id TEXT PRIMARY KEY, workspace TEXT, scope_type TEXT, scope_id TEXT, title TEXT, statement TEXT, context TEXT, conditions TEXT, procedure TEXT, exceptions TEXT, expected_outcome TEXT, counterexamples TEXT, confidence REAL, quality_score REAL, freshness REAL, status TEXT, sensitivity_level TEXT, source_type TEXT, created_by TEXT, created_at TEXT, updated_at TEXT);
        CREATE TABLE IF NOT EXISTS evidence (id TEXT PRIMARY KEY, experience_id TEXT, kind TEXT, content TEXT, source_ref TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS reviews (id TEXT PRIMARY KEY, experience_id TEXT, workspace TEXT, status TEXT, reason TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS questions (id TEXT PRIMARY KEY, workspace TEXT, question TEXT, context TEXT, status TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, workspace TEXT, agent_id TEXT, payload TEXT, created_at TEXT);
        """)
        self.db.commit()

    def insert_experience(self, workspace, data, source_type, created_by, evidence):
        # Exact statement match is deterministic deduplication for the first slice.
        existing = self.db.execute("SELECT * FROM experiences WHERE workspace=? AND lower(statement)=lower(?) AND status NOT IN ('rejected','deprecated')", (workspace, data["statement"])).fetchone()
        if existing:
            return dict(existing), "duplicate"
        eid = uid(); threshold = 0.92
        confidence = float(data.get("confidence", 0.6)); status = "approved" if confidence >= threshold and source_type == "explicit_teach" else "pending_review"
        ts = now()
        row = dict(id=eid, workspace=workspace, scope_type=data.get("scope_type","workspace"), scope_id=data.get("scope_id"), title=data["title"], statement=data["statement"], context=data.get("context",""), conditions=json.dumps(data.get("conditions",[]), ensure_ascii=False), procedure=json.dumps(data.get("procedure",[]), ensure_ascii=False), exceptions=json.dumps(data.get("exceptions",[]), ensure_ascii=False), expected_outcome=data.get("expected_outcome",""), counterexamples=json.dumps(data.get("counterexamples",[]), ensure_ascii=False), confidence=confidence, quality_score=float(data.get("quality_score", confidence)), freshness=1.0, status=status, sensitivity_level=data.get("sensitivity_level","normal"), source_type=source_type, created_by=created_by, created_at=ts, updated_at=ts)
        cols=','.join(row); self.db.execute(f"INSERT INTO experiences ({cols}) VALUES ({','.join('?' for _ in row)})", tuple(row.values()))
        self.db.execute("INSERT INTO evidence VALUES (?,?,?,?,?,?)", (uid(), eid, evidence.get("kind", source_type), evidence.get("content", data["statement"]), evidence.get("source_ref"), ts))
        if status != "approved": self.db.execute("INSERT INTO reviews VALUES (?,?,?,?,?,?)", (uid(), eid, workspace, "pending", "requires confirmation", ts))
        self.db.commit(); return row, status

    def search(self, workspace, query, scope_type=None, status="approved"):
        q = f"%{query.lower()}%"
        sql="SELECT * FROM experiences WHERE workspace=? AND status=? AND (lower(title) LIKE ? OR lower(statement) LIKE ? OR lower(context) LIKE ?)"
        args=[workspace,status,q,q,q]
        if scope_type: sql += " AND scope_type=?"; args.append(scope_type)
        rows=[dict(r) for r in self.db.execute(sql+" ORDER BY quality_score DESC, updated_at DESC LIMIT 20",args)]
        for r in rows:
            for k in ("conditions","procedure","exceptions","counterexamples"): r[k]=json.loads(r[k])
            r["provenance"]=[dict(x) for x in self.db.execute("SELECT kind,content,source_ref,created_at FROM evidence WHERE experience_id=?",(r["id"],))]
            r["conflict"] = False; r["needs_confirmation"] = r["status"] != "approved"
        return rows

store=Store()

def extract(payload, explicit=False):
    text = payload.get("text") or payload.get("message") or ""
    title = payload.get("title") or text[:80] or "Untitled experience"
    return {"title":title, "statement":text, "context":payload.get("context",""), "conditions":payload.get("conditions",[]), "procedure":payload.get("procedure",[]), "exceptions":payload.get("exceptions",[]), "expected_outcome":payload.get("expected_outcome",""), "counterexamples":payload.get("counterexamples",[]), "confidence":0.98 if explicit else float(payload.get("confidence",0.65)), "quality_score":float(payload.get("quality_score",0.8)), "scope_type":payload.get("scope_type","workspace"), "scope_id":payload.get("scope_id"), "sensitivity_level":payload.get("sensitivity_level","normal")}

def llm_call(system, user):
    key=os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY")
    base=(os.environ.get("OPENAI_BASE_URL") or os.environ.get("LLM_BASE_URL") or "").rstrip("/")
    model=os.environ.get("OPENAI_MODEL") or os.environ.get("LLM_MODEL")
    if not key or not base or not model: return {"ok":False,"error":"llm_not_configured"}
    if urlparse(base).path in ("", "/"):
        base += "/v1"
    req=urllib.request.Request(base+"/chat/completions", data=json.dumps({"model":model,"temperature":0.1,"messages":[{"role":"system","content":system},{"role":"user","content":user}]}).encode(), headers={"Content-Type":"application/json","Authorization":"Bearer "+key}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r: body=json.load(r)
        content=body["choices"][0]["message"]["content"]; return {"ok":True,"data":parse_json_content(content),"model":model}
    except urllib.error.HTTPError as e: return {"ok":False,"error":"upstream_http_error","status_code":e.code}
    except Exception as e: return {"ok":False,"error":type(e).__name__}

class Handler(BaseHTTPRequestHandler):
    def send_json(self, code, data):
        raw=json.dumps(data, ensure_ascii=False).encode(); self.send_response(code); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def body(self): return json.loads(self.rfile.read(int(self.headers.get("Content-Length",0))) or b"{}")
    def auth(self): return self.headers.get("X-API-Key") in {os.environ.get("EXPERIENCE_API_KEY","dev-key")}
    def do_GET(self):
        if self.path == "/health": return self.send_json(200,{"ok":True})
        if self.path == "/":
            try: raw=open(os.path.join(ROOT,"web","index.html"),encoding="utf-8").read()
            except OSError: raw="Experience Capture"
            out=raw.encode(); self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Content-Length",str(len(out))); self.end_headers(); self.wfile.write(out); return
        if not self.auth(): return self.send_json(401,{"error":"invalid_api_key"})
        if self.path == "/v1/reviews":
            rows=[dict(r) for r in store.db.execute("SELECT * FROM reviews WHERE status='pending' ORDER BY created_at")]; return self.send_json(200,{"items":rows})
        self.send_json(404,{"error":"not_found"})
    def do_POST(self):
        if not self.auth(): return self.send_json(401,{"error":"invalid_api_key"})
        path=urlparse(self.path).path; p=self.body(); ws=p.get("workspace_id","default"); agent=p.get("agent_id","anonymous")
        if path == "/v1/events":
            eid=uid(); store.db.execute("INSERT INTO events VALUES (?,?,?,?,?)",(eid,ws,agent,json.dumps(p,ensure_ascii=False),now())); store.db.commit(); return self.send_json(202,{"event_id":eid})
        if path in ("/v1/experiences/teach","/v1/experiences/ingest"):
            explicit=path.endswith("teach"); data,status=store.insert_experience(ws,extract(p,explicit),"explicit_teach" if explicit else "session_event",p.get("created_by",agent),{"kind":"user_statement" if explicit else "session_event","content":p.get("text") or p.get("message","")}); return self.send_json(201,{"experience":data,"status":status})
        if path == "/v1/experiences/search": return self.send_json(200,{"items":store.search(ws,p.get("query",""),p.get("scope_type"))})
        if path == "/v1/structure":
            raw_text=(p.get("text") or "").strip()
            if not raw_text: return self.send_json(400,{"ok":False,"error":"text_required"})
            result=llm_call(SYSTEM_PROMPT, "请结构化下面这条人类经验：\n\n"+raw_text)
            if not result.get("ok"): return self.send_json(502,result)
            record=result["data"]
            record["schema_version"]=SCHEMA_VERSION
            source=record.setdefault("source",{})
            source["raw_text"]=raw_text
            source.setdefault("language","zh-CN")
            source.setdefault("source_type","human_explicit")
            errors=validate_record(record,raw_text)
            if errors: return self.send_json(422,{"ok":False,"error":"schema_validation_failed","validation_errors":errors,"model":result.get("model")})
            return self.send_json(200,{"ok":True,"record":record,"markdown":render_markdown(record),"model":result.get("model")})
        if path == "/v1/llm/extract":
            raw_text=(p.get("text") or "").strip()
            result=llm_call(SYSTEM_PROMPT,"请结构化下面这条人类经验：\n\n"+raw_text); return self.send_json(200,result)
        if path == "/v1/llm/scenario":
            memories=store.search(ws,p.get("query","")); prompt="场景：\n"+p.get("scenario","")+"\n\n可用经验：\n"+json.dumps(memories,ensure_ascii=False)
            result=llm_call("你是严谨的仿真工程助手。根据给定经验修正回答；若经验不适用，明确说明。只返回 JSON，字段为 answer, applied_experience_ids, caveats。", prompt); return self.send_json(200,result)
        if path == "/v1/questions/propose":
            qid=uid(); store.db.execute("INSERT INTO questions VALUES (?,?,?,?,?,?)",(qid,ws,p.get("question","What should I remember?"),json.dumps(p.get("context",{}),ensure_ascii=False),"open",now())); store.db.commit(); return self.send_json(201,{"question_id":qid,"question":p.get("question","What should I remember?")})
        if path.startswith("/v1/questions/") and path.endswith("/answer"):
            answer=p.get("answer",""); data,status=store.insert_experience(ws,extract({"text":answer,"context":p.get("context",{})},True),"question_answer",agent,{"kind":"question_answer","content":answer}); return self.send_json(201,{"experience":data,"status":status})
        if path.startswith("/v1/reviews/"):
            rid=path.rsplit("/",1)[-1]; action=p.get("action"); row=store.db.execute("SELECT experience_id FROM reviews WHERE id=?",(rid,)).fetchone()
            if not row: return self.send_json(404,{"error":"review_not_found"})
            allowed={"approve":"approved","reject":"rejected","deprecate":"deprecated","supersede":"superseded"}; status=allowed.get(action)
            if not status: return self.send_json(400,{"error":"invalid_action"})
            store.db.execute("UPDATE experiences SET status=?,updated_at=? WHERE id=?",(status,now(),row[0])); store.db.execute("UPDATE reviews SET status=?,reason=? WHERE id=?",(status,p.get("reason",""),rid)); store.db.commit(); return self.send_json(200,{"experience_id":row[0],"status":status})
        self.send_json(404,{"error":"not_found"})

if __name__ == "__main__":
    port=int(os.environ.get("PORT","8080")); print(f"experience-capture listening on http://127.0.0.1:{port}"); ThreadingHTTPServer(("0.0.0.0",port),Handler).serve_forever()
