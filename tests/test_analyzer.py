from pathlib import Path

import pytest

from backend.analyzer import RULES, analyze, detect_language, language_from_name

SAMPLES = Path(__file__).resolve().parent.parent / "backend" / "samples"


def flat(rule):
    return {"severity": rule.severity, "confidence": 1.0, "probs": {}, "risk": 0}


def run(code, lang):
    return analyze(code, lang, flat)


def rule_ids(result):
    return sorted(f["ruleId"] for f in result["findings"])


EXPECTED = {
    "checkout.js": ["assign-cond", "console", "empty-catch", "eval", "innerhtml", "loose-eq", "nesting", "offbyone", "var", "var", "var"],
    "auth.py": ["bare-except", "none-eq", "secret", "sqli", "star-import"],
    "report_export.py": ["mutable-default", "open-no-with", "pickle", "print", "shell", "todo"],
    "cart.js": ["await-in-loop", "parseint", "promise-no-catch", "todo"],
    "utils.js": ["loose-eq"],
}


@pytest.mark.parametrize("name,expected", EXPECTED.items())
def test_sample_files(name, expected):
    code = (SAMPLES / name).read_text()
    assert rule_ids(run(code, language_from_name(name))) == sorted(expected)


def test_each_rule_has_a_unique_id_and_valid_fields():
    ids = [r.id for r in RULES]
    assert len(ids) == len(set(ids))
    for r in RULES:
        assert r.lang in ("js", "py", "any")
        assert r.severity in ("critical", "high", "medium", "low")
        assert r.why and r.fix and r.fix_code and r.description


def test_strings_and_comments_do_not_trigger_rules():
    js = 'const a = "call eval(x) here";\n// eval(y) in a comment\nconst b = "x == y";\n'
    assert rule_ids(run(js, "js")) == []
    py = 'msg = "use print(x) and except: here"\n# print("hi")\n'
    assert rule_ids(run(py, "py")) == []


def test_int_input_rule_for_the_student_script():
    code = 'name = input("Enter your name: ")\nage = int(input("Enter your age: "))\nprint("Name:", name)\n'
    ids = rule_ids(run(code, "py"))
    assert "int-input" in ids and ids.count("print") == 1


def test_clean_code_scores_100():
    r = run("function add(a, b) {\n  return a + b;\n}\n", "js")
    assert r["findings"] == [] and r["score"] == 100 and r["grade"] == "A"


def test_score_drops_with_severity():
    bad = run('eval(userInput);\nel.innerHTML = x;\n', "js")
    mild = run("var a = 1;\nvar b = 2;\n", "js")
    assert bad["score"] < mild["score"] < 100


def test_findings_are_sorted_by_risk_then_line():
    def by_rule(rule):
        risk = {"critical": 90, "high": 70, "medium": 40, "low": 10}[rule.severity]
        return {"severity": rule.severity, "confidence": 1.0, "probs": {}, "risk": risk}

    r = analyze('var a = 1;\neval(x);\n', "js", by_rule)
    assert [f["ruleId"] for f in r["findings"]] == ["eval", "var"]


def test_windows_line_endings():
    r = run("var a = 1;\r\neval(x);\r\n", "js")
    assert sorted((f["ruleId"], f["line"]) for f in r["findings"]) == [("eval", 2), ("var", 1)]


def test_a_crashing_rule_never_breaks_the_scan(monkeypatch):
    import backend.analyzer.engine as engine
    from backend.analyzer.rules import Rule

    boom = Rule("boom", "any", "Code quality", "low", "t", "d", "w", "f", "c", lambda *a: 1 / 0)
    monkeypatch.setattr(engine, "RULES", [boom] + list(RULES))
    assert rule_ids(analyze("eval(x);\n", "js", flat)) == ["eval"]


def test_language_detection():
    assert detect_language('name = input("x")\nprint(name)\n') == "py"
    assert detect_language("const a = 1;\nconsole.log(a);\n") == "js"
    assert language_from_name("a.py") == "py" and language_from_name("a.mjs") == "js" and language_from_name("a.txt") is None
