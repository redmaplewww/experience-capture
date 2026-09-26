import json
import os
import sys
import threading
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
import server
from experience_standard import empty_record, item


raw = "设备发出异响时先停机，再检查轴承温度。"
record = empty_record(raw)
record["identity"] = {"title": "异响停机检查", "summary": "设备异响后先停机并检查轴承温度。", "primary_type": "procedure", "secondary_types": ["diagnostic"]}
record["situation"]["triggers"] = [item("设备发出异响")]
record["guidance"]["steps"] = [item("先停机"), item("检查轴承温度")]
record["evidence"]["confidence"] = 0.98
record["indexing"]["domains"] = ["设备维护"]
record["indexing"]["tasks"] = ["故障检查"]
record["indexing"]["tags"] = ["异响", "停机", "轴承温度"]

server.llm_call = lambda system, user: {"ok": True, "data": record, "model": "fake-structure-model"}
httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
thread = threading.Thread(target=httpd.serve_forever, daemon=True)
thread.start()
base = f"http://127.0.0.1:{httpd.server_port}"

try:
    with urllib.request.urlopen(base + "/") as response:
        assert response.status == 200
    request = urllib.request.Request(
        base + "/v1/structure",
        data=json.dumps({"text": raw}, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json", "X-API-Key": "dev-key"},
        method="POST",
    )
    with urllib.request.urlopen(request) as response:
        result = json.load(response)
    assert result["ok"] is True
    assert result["record"]["source"]["raw_text"] == raw
    assert result["record"]["guidance"]["steps"][0]["basis"] == "explicit"
    assert "异响停机检查" in result["markdown"]
    print("structure API: PASS")
finally:
    httpd.shutdown()
    httpd.server_close()
