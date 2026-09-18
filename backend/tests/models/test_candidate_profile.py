from app.models.candidate_profile import CandidateProfile


def test_table_name_and_columns() -> None:
    columns = CandidateProfile.__table__.columns

    assert CandidateProfile.__tablename__ == "candidate_profiles"
    assert {c.name for c in columns} == {
        "id",
        "user_id",
        "education",
        "experience",
        "projects",
        "skills",
        "github_url",
        "created_at",
    }


def test_user_id_has_no_default() -> None:
    assert CandidateProfile.__table__.c.user_id.default is None


def test_github_url_is_nullable() -> None:
    assert CandidateProfile.__table__.c.github_url.nullable is True


def test_user_id_is_a_cascading_foreign_key_to_users() -> None:
    fks = CandidateProfile.__table__.c.user_id.foreign_keys
    assert {fk.target_fullname for fk in fks} == {"users.id"}
    assert {fk.ondelete for fk in fks} == {"CASCADE"}
