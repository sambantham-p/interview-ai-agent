from app.models.email_otp import EmailOTP


def test_email_otp_table_name_and_columns() -> None:
    columns = EmailOTP.__table__.columns

    assert EmailOTP.__tablename__ == "email_otps"
    assert {c.name for c in columns} == {
        "id",
        "email",
        "name",
        "password_hash",
        "otp_code",
        "expires_at",
        "is_used",
        "created_at",
    }


def test_email_otp_nullability() -> None:
    assert EmailOTP.__table__.c.email.nullable is False
    assert EmailOTP.__table__.c.otp_code.nullable is False
    assert EmailOTP.__table__.c.expires_at.nullable is False
    assert EmailOTP.__table__.c.is_used.nullable is False
