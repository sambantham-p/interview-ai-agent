from app.constants.question_bank import QUESTION_EMBEDDING_DIM
from app.models.technical_question import TechnicalQuestion


def test_table_name_and_columns() -> None:
    columns = TechnicalQuestion.__table__.columns

    assert TechnicalQuestion.__tablename__ == "technical_questions"
    assert {c.name for c in columns} == {
        "id",
        "question_text",
        "topic",
        "tech_stack",
        "difficulty",
        "seniority",
        "embedding",
        "created_at",
    }


def test_tech_stack_defaults_to_an_empty_list() -> None:
    assert TechnicalQuestion.__table__.c.tech_stack.default.arg(None) == []


def test_embedding_dimension_matches_the_embedding_model() -> None:
    assert TechnicalQuestion.__table__.c.embedding.type.dim == QUESTION_EMBEDDING_DIM


def test_topic_difficulty_and_seniority_are_indexed() -> None:
    # These are the fields RAG retrieval would ever want to filter/group
    # by alongside the vector similarity search.
    assert TechnicalQuestion.__table__.c.topic.index is True
    assert TechnicalQuestion.__table__.c.difficulty.index is True
    assert TechnicalQuestion.__table__.c.seniority.index is True
