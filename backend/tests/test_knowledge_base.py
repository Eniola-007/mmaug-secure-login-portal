import pytest

from app.knowledge_base import load_role_knowledge


def test_student_knowledge_is_role_isolated() -> None:
    knowledge = load_role_knowledge("student")

    assert "# Student guidance" in knowledge
    assert "# Assistant guardrails" in knowledge
    assert "# Teacher guidance" not in knowledge
    assert "# Administrator guidance" not in knowledge


def test_visitor_knowledge_contains_only_public_sources() -> None:
    knowledge = load_role_knowledge("visitor")

    assert "# MMAUG High School secure portal" in knowledge
    assert "# Assistant guardrails" in knowledge
    assert "# Student guidance" not in knowledge


def test_unknown_audience_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unsupported assistant audience"):
        load_role_knowledge("owner")
