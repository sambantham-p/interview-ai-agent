from app.models.user import User


def test_user_table_name_and_columns() -> None:
    columns = User.__table__.columns

    assert User.__tablename__ == "users"
    assert {c.name for c in columns} == {
        "id",
        "email",
        "name",
        "picture",
        "preferred_name",
        "password_hash",
        "auth_provider",
        "google_id",
        "is_verified",
        "token_version",
        "created_at",
        "updated_at",
    }


def test_user_column_nullability() -> None:
    assert User.__table__.c.email.nullable is False
    assert User.__table__.c.name.nullable is False
    assert User.__table__.c.picture.nullable is True
    assert User.__table__.c.password_hash.nullable is True
    assert User.__table__.c.google_id.nullable is True
    assert User.__table__.c.is_verified.nullable is False
    assert User.__table__.c.token_version.nullable is False
