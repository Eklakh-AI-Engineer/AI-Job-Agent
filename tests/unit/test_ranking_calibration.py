from backend.evaluation.calibration import CALIBRATION_VERSION, fit_sigmoid


def test_sigmoid_calibrator_is_monotonic_and_bounded():
    scores = [10, 20, 25, 30, 40, 50, 55, 60, 70, 80, 90, 95]
    labels = [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1]
    calibrator = fit_sigmoid(scores, labels)
    values = [calibrator.probability(x) for x in scores]
    assert calibrator.version == CALIBRATION_VERSION
    assert all(0.0 <= value <= 1.0 for value in values)
    assert values == sorted(values)
    assert calibrator.score(70) > calibrator.score(50)
