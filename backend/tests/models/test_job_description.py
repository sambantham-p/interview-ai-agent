from app.models.job_description import JobDescription


def test_table_name_and_columns() -> None:
    columns = JobDescription.__table__.columns

    assert JobDescription.__tablename__ == "job_descriptions"
    assert {c.name for c in columns} == {
        "id",
        "user_id",
        "role",
        "company_name",
        "seniority",
        "tech_stack",
        "coding_assessment_expected",
        "created_at",
    }


def test_user_id_has_no_default() -> None:
    assert JobDescription.__table__.c.user_id.default is None


def test_coding_assessment_expected_defaults_to_false() -> None:
    assert JobDescription.__table__.c.coding_assessment_expected.default.arg is False


def test_user_id_is_a_cascading_foreign_key_to_users() -> None:
    fks = JobDescription.__table__.c.user_id.foreign_keys
    assert {fk.target_fullname for fk in fks} == {"users.id"}
    assert {fk.ondelete for fk in fks} == {"CASCADE"}
