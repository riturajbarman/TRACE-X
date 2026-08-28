import uuid
import numpy as np
import pytest
from datetime import datetime, timezone
import json

from app.domain.event.models import Event
from app.domain.anomaly.features import extract_features
from app.domain.anomaly.model import AnomalyModel

def test_feature_extraction_from_event():
    e = Event()
    e.event_type = "process_exec"
    e.source = "evtx"
    e.timestamp = datetime(2025, 1, 1, 14, 30, 0, tzinfo=timezone.utc)  # hour 14, wednesday (2)
    e.data = {
        "process_name": "cmd.exe",
        "path": "C:\\Windows\\System32",
        "command_line": "cmd.exe /c echo hello"
    }
    
    features = extract_features(e)
    assert len(features) == 10
    
    assert features[0] == 1.0  # process_exec
    assert features[1] == 1.0  # evtx
    assert features[2] == 14.0 # hour
    assert features[3] == 2.0  # wednesday
    assert features[4] > 0     # size > 0
    assert features[5] == 1.0  # has_process_name
    assert features[6] == 0.0  # has_network
    assert features[7] == 0.0  # has_registry
    assert features[8] == 1.0  # has_path
    assert features[9] == 0.0  # keyword score (no suspicious keywords)

def test_feature_extraction_empty_data():
    e = Event()
    e.timestamp = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    
    features = extract_features(e)
    assert len(features) == 10
    assert features[0] == 0.0 # generic
    assert features[1] == 0.0 # test
    assert features[5] == 0.0 # no process
    assert features[4] == 2.0 # '{}'

def test_model_is_deterministic():
    X = np.random.RandomState(42).rand(100, 10)
    
    model1 = AnomalyModel(random_state=42, contamination=0.1)
    model1.fit(X)
    is_anom1, scores1 = model1.predict(X)
    
    model2 = AnomalyModel(random_state=42, contamination=0.1)
    model2.fit(X)
    is_anom2, scores2 = model2.predict(X)
    
    np.testing.assert_array_equal(is_anom1, is_anom2)
    np.testing.assert_array_almost_equal(scores1, scores2)

def test_empty_input_handled():
    model = AnomalyModel()
    model.fit(np.array([]))
    is_anom, scores = model.predict(np.array([]))
    assert len(is_anom) == 0
    assert len(scores) == 0

def test_anomaly_score_is_bounded():
    X = np.random.RandomState(42).rand(100, 10)
    model = AnomalyModel(random_state=42, contamination=0.1)
    model.fit(X)
    _, scores = model.predict(X)
    assert np.all(scores >= 0)
    assert np.all(scores <= 100)

def test_explanation_is_present():
    X_train = np.zeros((10, 10))
    model = AnomalyModel(random_state=42, contamination=0.1)
    model.fit(X_train)
    
    # Anomaly with high value on feature 5 (has_process_name)
    x_test = np.zeros((1, 10))
    x_test[0, 5] = 1.0
    
    expl = model.explain(x_test[0])
    assert "has_process_name" in expl

def test_model_versioning():
    model = AnomalyModel()
    assert model.VERSION == "1.0.0"

def test_false_positive_rate_measurement():
    """
    Load the synthetic datasets and evaluate the model.
    """
    with open("tests/fixtures/anomaly/normal_events.json", "r") as f:
        normal_data = json.load(f)
    
    with open("tests/fixtures/anomaly/anomalous_events.json", "r") as f:
        anom_data = json.load(f)
        
    with open("tests/fixtures/anomaly/ground_truth.json", "r") as f:
        ground_truth = json.load(f)
        
    def to_event(d):
        e = Event()
        e.id = uuid.UUID(d["id"])
        e.event_type = d.get("event_type")
        e.source = d.get("source")
        e.timestamp = datetime.fromisoformat(d["timestamp"])
        e.data = d.get("data")
        return e
        
    normal_events = [to_event(d) for d in normal_data]
    anom_events = [to_event(d) for d in anom_data]
    
    X_train = np.array([extract_features(e) for e in normal_events])
    
    model = AnomalyModel(random_state=42, contamination=0.1)
    model.fit(X_train)
    
    all_events = normal_events + anom_events
    X_eval = np.array([extract_features(e) for e in all_events])
    
    is_anomaly, scores = model.predict(X_eval)
    
    tp = 0
    fp = 0
    tn = 0
    fn = 0
    
    for i, evt in enumerate(all_events):
        pred = is_anomaly[i]
        actual = ground_truth[str(evt.id)]["is_anomaly"]
        
        if pred and actual:
            tp += 1
        elif pred and not actual:
            fp += 1
        elif not pred and not actual:
            tn += 1
        elif not pred and actual:
            fn += 1
            
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
    
    print(f"\n[Phase 9 Anomaly Detection Evaluation]")
    print(f"  Dataset: {len(normal_events)} normal + {len(anom_events)} anomalous events")
    print(f"  True Positives:   {tp}")
    print(f"  False Positives:  {fp}")
    print(f"  True Negatives:   {tn}")
    print(f"  False Negatives:  {fn}")
    print(f"  Precision:        {precision:.3f}")
    print(f"  Recall:           {recall:.3f}")
    print(f"  F1:               {f1:.3f}")
    print(f"  FPR:              {fpr:.3f}")
    
    assert fpr <= 0.20, f"False positive rate {fpr} exceeds threshold 0.20"
