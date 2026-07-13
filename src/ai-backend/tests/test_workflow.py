from app.workflow import PharmaAgent


def test_emergency_questions_are_stopped_before_model_work():
    result = PharmaAgent().answer("I have difficulty breathing after taking this medicine")
    assert result.risk_level == "emergency"
    assert "emergency services" in result.answer


def test_high_risk_questions_are_classified():
    assert PharmaAgent().classify("What is the dosage?") == "high"
