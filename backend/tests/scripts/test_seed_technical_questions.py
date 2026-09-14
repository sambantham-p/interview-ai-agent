import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "seed_technical_questions",
    Path(__file__).parent.parent.parent / "scripts" / "seed_technical_questions.py",
)
seed_technical_questions = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(seed_technical_questions)

QUESTIONS = seed_technical_questions.QUESTIONS

_VALID_DIFFICULTIES = {"easy", "medium", "hard"}
_VALID_SENIORITIES = {"entry", "mid", "senior"}
_REQUIRED_KEYS = {"question_text", "topic", "tech_stack", "difficulty", "seniority"}


def test_bank_has_a_real_amount_of_content() -> None:
    # Per CLAUDE.md's RAG Architecture: a moderate starter set (~40-50),
    # not a token demo set.
    assert 40 <= len(QUESTIONS) <= 50


def test_every_entry_has_exactly_the_required_fields() -> None:
    for entry in QUESTIONS:
        assert set(entry.keys()) == _REQUIRED_KEYS


def test_every_question_text_is_unique() -> None:
    texts = [entry["question_text"] for entry in QUESTIONS]
    assert len(texts) == len(set(texts))


def test_every_difficulty_and_seniority_is_a_valid_value() -> None:
    for entry in QUESTIONS:
        assert entry["difficulty"] in _VALID_DIFFICULTIES
        assert entry["seniority"] in _VALID_SENIORITIES


def test_every_question_text_is_non_trivial() -> None:
    # Catches an accidentally truncated/placeholder entry.
    for entry in QUESTIONS:
        assert len(entry["question_text"]) >= 20


def test_covers_every_topic_claimed_in_claude_md() -> None:
    # DBMS, OS, networking, OOP, system design basics, common languages -
    # per CLAUDE.md's RAG Architecture description of the bank's coverage.
    topics = {entry["topic"] for entry in QUESTIONS}
    assert {
        "DBMS",
        "OS",
        "Networking",
        "OOP",
        "System Design",
        "Python",
        "JavaScript",
    } <= topics
