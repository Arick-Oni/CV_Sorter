import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.services.llm_ranking import normalize_weights, score_cv_criterion

def test_normalize_weights_basic():
    # Test normalization when parent weights do not sum to 100
    criteria = [
        {"name": "A", "weight": 40, "subcriteria": [{"name": "A1", "weight": 20, "required": True}, {"name": "A2", "weight": 20, "required": True}]},
        {"name": "B", "weight": 40, "subcriteria": [{"name": "B1", "weight": 10, "required": True}]}
    ]
    normalized = normalize_weights(criteria)
    # Check parent weights sum to 100
    assert sum(c["weight"] for c in normalized) == 100
    # Check subcriteria weights sum to parent weight
    for c in normalized:
        assert sum(s["weight"] for s in c["subcriteria"]) == c["weight"]

def test_normalize_weights_zero():
    # Test normalization when weights are zero
    criteria = [
        {"name": "A", "weight": 0, "subcriteria": []},
        {"name": "B", "weight": 0, "subcriteria": []}
    ]
    normalized = normalize_weights(criteria)
    assert sum(c["weight"] for c in normalized) == 100
    for c in normalized:
        assert len(c["subcriteria"]) == 1
        assert sum(s["weight"] for s in c["subcriteria"]) == c["weight"]

def test_score_cv_criterion_math_mock():
    # We mock _ollama_chat inside llm_ranking to return a pre-determined JSON
    import backend.services.llm_ranking as lr
    
    original_ollama_chat = lr._ollama_chat
    
    mock_response = {
        "subcriteria": [
            {"name": "C#", "score": 1.0, "evidence": "C# developer for 5 years"},
            {"name": "ASP.NET MVC", "score": 0.75, "evidence": "Used ASP.NET MVC in two projects"},
            {"name": "Angular", "score": 0.0, "evidence": "No mention"}
        ],
        "score": 50.0, # LLM returned score (should be overridden by python calculation)
        "justification": "Candidate has strong C# and ASP.NET MVC background but lacks Angular."
    }
    
    import json
    lr._ollama_chat = lambda *args, **kwargs: json.dumps(mock_response)
    
    criterion = {
        "name": "Microsoft Stack",
        "weight": 35,
        "description": "Skills in Microsoft technologies",
        "subcriteria": [
            {"name": "C#", "weight": 15, "required": True},
            {"name": "ASP.NET MVC", "weight": 10, "required": True},
            {"name": "Angular", "weight": 10, "required": False}
        ]
    }
    
    try:
        res = lr.score_cv_criterion(criterion, "some cv text", "http://mock", "mock-model")
        # Expected calculation:
        # C#: 1.0 * 15 = 15
        # ASP.NET MVC: 0.75 * 10 = 7.5
        # Angular: 0.0 * 10 = 0
        # Sum = 22.5
        # Computed Score = (22.5 / 35) * 100 = 64.2857 -> round to 64.29
        assert res["score"] == 64.29
        assert len(res["subcriteria_breakdown"]) == 3
        assert res["subcriteria_breakdown"][0]["score"] == 1.0
        assert res["subcriteria_breakdown"][1]["score"] == 0.75
        assert res["subcriteria_breakdown"][2]["score"] == 0.0
    finally:
        lr._ollama_chat = original_ollama_chat

if __name__ == "__main__":
    test_normalize_weights_basic()
    test_normalize_weights_zero()
    test_score_cv_criterion_math_mock()
    print("All tests passed!")
