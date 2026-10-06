from backend.evaluation.outcome_metrics import application_funnel, apply_rate_by_score_bucket, transition_rate

def test_application_funnel_is_stable():
    result = application_funnel(["Discovered", "Matched", "Applied", "Rejected"])
    assert result["Discovered"] == 1
    assert result["Approved"] == 0
    assert result["Applied"] == 1

def test_score_bucket_apply_rate():
    result = apply_rate_by_score_bucket([
        {"match_score": 85, "status": "Applied"},
        {"match_score": 82, "status": "Rejected"},
        {"match_score": 55, "status": "Applied"},
    ])
    assert result["80-100"] == 0.5
    assert result["40-59"] == 1.0

def test_transition_rate():
    events = [{"from_status": "Matched", "to_status": "Approved"}, {"from_status": "Matched", "to_status": "Rejected"}]
    assert transition_rate("Matched", "Approved", events) == 0.5
