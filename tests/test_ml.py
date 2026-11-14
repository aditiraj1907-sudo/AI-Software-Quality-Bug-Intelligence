from ml.model import SEVERITIES, get_model


def test_metrics_are_better_than_guessing():
    m = get_model().metrics
    assert m["samples"] >= 100
    assert m["severity"]["accuracy"] > 0.30  # four classes: random guessing is 0.25
    assert m["category"]["accuracy"] > 0.40  # seven classes: random guessing is 0.14


def test_probabilities_sum_to_one():
    p = get_model().severity_probs("sql injection in the login form")
    assert set(p) == set(SEVERITIES)
    assert abs(sum(p.values()) - 1) < 1e-6


def test_obvious_cases():
    model = get_model()
    assert model.predict("Admin login can be bypassed with an empty password exposing all customer data")["severity"] == "critical"
    assert model.predict("Typo in the tooltip on the settings page")["severity"] == "low"
    r = model.predict("Checkout crashes with a null pointer when the customer profile is missing")
    assert r["severity"] in ("critical", "high") and r["category"] == "Error handling"


def test_explanation_lists_terms_that_were_in_the_text():
    r = get_model().predict("payment is charged twice when the user taps pay quickly")
    assert r["topTerms"] and all(any(w in "payment is charged twice when the user taps pay quickly" for w in t.split()) for t in r["topTerms"])


def test_unknown_words_give_no_terms():
    r = get_model().predict("xyzzy plugh")
    assert r["topTerms"] == [] and r["knownTerms"] == 0
