def test_health(client):
    r = client.get("/api/health").json()
    assert r["status"] == "ok" and r["rules"] == 27


def test_new_database_starts_with_the_sample_project(client):
    p = client.get("/api/project").json()
    assert [f["name"] for f in p["files"]] == ["checkout.js", "auth.py", "report_export.py", "cart.js", "utils.js"]
    assert p["stats"]["issues"] == 27
    assert sum(p["stats"]["counts"].values()) == 27
    assert len(p["history"]) == 5  # one snapshot per file added


def test_analyze_does_not_save(client):
    r = client.post("/api/analyze", json={"code": "eval(x);\nvar a = 1;\n", "language": "js"})
    assert r.status_code == 200
    body = r.json()
    assert {f["ruleId"] for f in body["findings"]} == {"eval", "var"}
    assert client.get("/api/project").json()["stats"]["issues"] == 27


def test_analyze_auto_detects_python(client):
    code = 'age = int(input("Enter your age: "))\nprint("Age:", age)\n'
    body = client.post("/api/analyze", json={"code": code}).json()
    assert body["language"] == "py"
    assert {f["ruleId"] for f in body["findings"]} == {"int-input", "print"}


def test_analyze_rejects_blank_code(client):
    r = client.post("/api/analyze", json={"code": "   \n"})
    assert r.status_code == 422
    assert "Paste some code" in r.json()["detail"][0]["msg"]


def test_analyze_rejects_huge_code(client):
    assert client.post("/api/analyze", json={"code": "a" * 200_001}).status_code == 422


def test_add_and_remove_file(client):
    r = client.post("/api/project/files", json={"code": "eval(x);\n", "language": "js"})
    assert r.status_code == 201
    added = r.json()
    assert added["name"].startswith("snippet-") and added["issues"] == 1
    p = client.get("/api/project").json()
    assert len(p["files"]) == 6 and p["stats"]["issues"] == 28 and len(p["history"]) == 6
    assert client.delete(f"/api/project/files/{added['id']}").status_code == 200
    p = client.get("/api/project").json()
    assert len(p["files"]) == 5 and p["stats"]["issues"] == 27
    assert client.delete(f"/api/project/files/{added['id']}").status_code == 404


def test_findings_are_removed_with_their_file(client):
    first = client.get("/api/project").json()["files"][0]
    client.delete(f"/api/project/files/{first['id']}")
    names = {f["file"] for f in client.get("/api/findings").json()}
    assert first["name"] not in names


def test_findings_filters(client):
    allf = client.get("/api/findings").json()
    assert len(allf) == 27
    risks = [f["risk"] for f in allf]
    assert risks == sorted(risks, reverse=True)
    crit = client.get("/api/findings", params={"severity": "critical"}).json()
    assert crit and all(f["severity"] == "critical" for f in crit)
    sec = client.get("/api/findings", params={"category": "Security", "file": "auth.py"}).json()
    assert sec and all(f["category"] == "Security" and f["file"] == "auth.py" for f in sec)
    assert client.get("/api/findings", params={"severity": "bogus"}).status_code == 422


def test_finding_shape(client):
    f = client.get("/api/findings").json()[0]
    for key in ("file", "ruleId", "line", "code", "category", "title", "severity", "confidence", "risk", "why", "fix", "fixCode", "probs"):
        assert key in f
    assert abs(sum(f["probs"].values()) - 1) < 1e-6


def test_reset_restores_samples(client):
    for f in client.get("/api/project").json()["files"]:
        client.delete(f"/api/project/files/{f['id']}")
    assert client.get("/api/project").json()["files"] == []
    assert client.get("/api/project").json()["stats"]["score"] == 100
    p = client.post("/api/project/reset").json()
    assert len(p["files"]) == 5 and p["stats"]["issues"] == 27


def test_report(client):
    r = client.get("/api/report").json()
    assert r["files"] == 5
    md = r["markdown"]
    assert md.startswith("# Software quality report")
    assert "## Highest-risk issues" in md and "checkout.js" in md and "## Recommendations" in md


def test_report_for_empty_project(client):
    for f in client.get("/api/project").json()["files"]:
        client.delete(f"/api/project/files/{f['id']}")
    md = client.get("/api/report").json()["markdown"]
    assert "0 issues found" in md and "No issues were found" in md


def test_predict(client):
    r = client.post("/api/predict", json={"text": "Typo in the tooltip on the settings page"}).json()
    assert r["severity"] == "low" and r["category"] and r["topTerms"]
    assert abs(sum(r["severityProbabilities"].values()) - 1) < 1e-6
    assert client.post("/api/predict", json={"text": "hi"}).status_code == 422


def test_rules_and_model_info(client):
    rules = client.get("/api/rules").json()
    assert len(rules) == 27 and {"id", "title", "category", "defaultSeverity", "predictedSeverity"} <= set(rules[0])
    m = client.get("/api/model").json()
    assert m["samples"] >= 100 and "accuracy" in m["severity"] and "accuracy" in m["category"]


def test_samples_endpoint(client):
    s = client.get("/api/samples").json()
    assert [x["name"] for x in s] == ["checkout.js", "auth.py", "report_export.py", "cart.js", "utils.js"]
    assert all(x["code"].strip() for x in s)


def test_data_survives_a_restart(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from backend.main import app

    monkeypatch.setenv("QBI_DB", str(tmp_path / "persist.db"))
    with TestClient(app) as c:
        c.post("/api/project/files", json={"code": "eval(x);\n", "language": "js"})
    with TestClient(app) as c:  # second start must not re-seed or lose data
        files = c.get("/api/project").json()["files"]
    assert len(files) == 6
