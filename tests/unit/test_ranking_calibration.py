from backend.evaluation.calibration import calibrate, normalize_weights, mse

def test_normalize_weights_sums_to_one():
    weights=normalize_weights({"semantic":2,"technical":1})
    assert abs(sum(weights.values())-1.0)<1e-9

def test_calibration_is_deterministic():
    rows=[]
    for i in range(30):
        strong=100.0 if i%2==0 else 10.0
        rows.append({"features":{"semantic":strong,"technical":strong,"role":50,"experience":50,"education":50,"preference":50,"evidence":strong},"relevance":4 if i%2==0 else 0})
    a=calibrate(rows); b=calibrate(rows)
    assert a==b
    assert mse(rows,a) <= mse(rows,normalize_weights({"semantic":.25,"technical":.30,"role":.15,"experience":.10,"education":.05,"preference":.10,"evidence":.05}))
