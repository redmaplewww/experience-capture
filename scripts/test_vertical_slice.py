import json, os, socket, subprocess, sys, tempfile, time, urllib.request

root = os.path.dirname(os.path.dirname(__file__))
db = os.path.join(tempfile.gettempdir(), "experience-capture-test.db")
try:
    os.remove(db)
except FileNotFoundError:
    pass
with socket.socket() as probe:
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
env = os.environ.copy()
env["EXPERIENCE_DB"] = db
env["PORT"] = str(port)
p = subprocess.Popen([sys.executable, os.path.join(root, "scripts", "server.py")], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
time.sleep(.4)

def call(path, payload):
    req = urllib.request.Request(f"http://127.0.0.1:{port}" + path, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", "X-API-Key": "dev-key"}, method="POST")
    with urllib.request.urlopen(req) as r:
        return r.status, json.load(r)

try:
    status, taught = call("/v1/experiences/teach", {"workspace_id":"a", "agent_id":"agent-1", "text":"在部署前先运行迁移检查", "conditions":["数据库版本已锁定"], "procedure":["执行迁移检查"], "expected_outcome":"迁移可重复"})
    assert status == 201 and taught["status"] == "approved"
    _, ingested = call("/v1/experiences/ingest", {"workspace_id":"a", "agent_id":"agent-1", "text":"临时观察：先运行迁移检查", "confidence":.5})
    assert ingested["status"] == "pending_review"
    _, results = call("/v1/experiences/search", {"workspace_id":"a", "query":"迁移检查"})
    assert results["items"] and results["items"][0]["provenance"]
    _, other = call("/v1/experiences/search", {"workspace_id":"b", "query":"迁移检查"})
    assert other["items"] == []
    print("vertical slice: PASS")
finally:
    p.terminate()
    p.wait(timeout=3)
