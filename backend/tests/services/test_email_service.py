import smtplib

from pytest_mock import MockerFixture

from app.constants.auth import OTP_EXPIRY_MINUTES, PASSWORD_RESET_EXPIRY_MINUTES
from app.core.config import SMTPSettings
from app.services.email_service import (
    render_otp_email_html,
    render_password_reset_email_html,
    send_password_reset_email,
    send_verification_email,
)


def test_render_otp_email_html() -> None:
    html = render_otp_email_html("Jane Doe", "849201")

    assert "Prepwise" in html
    assert "Jane Doe" in html
    assert f"{OTP_EXPIRY_MINUTES} minutes" in html
    assert "Security notice" in html
    for d in "849201":
        assert f">{d}</div>" in html


def test_render_password_reset_email_html() -> None:
    html = render_password_reset_email_html("Jane Doe", "849201")

    assert "Prepwise" in html
    assert "Jane Doe" in html
    assert f"{PASSWORD_RESET_EXPIRY_MINUTES} minutes" in html
    assert "Security notice" in html
    for d in "849201":
        assert f">{d}</div>" in html


async def test_send_password_reset_email_local_dev_without_smtp(
    mocker: MockerFixture,
) -> None:
    mocker.patch(
        "app.services.email_service.get_smtp_settings",
        return_value=SMTPSettings(),
    )

    success = await send_password_reset_email("jane@example.com", "Jane", "123456")
    assert success is True


async def test_send_password_reset_email_via_smtp_success(
    mocker: MockerFixture,
) -> None:
    mocker.patch(
        "app.services.email_service.get_smtp_settings",
        return_value=SMTPSettings(
            smtp_host="smtp.example.com",
            smtp_user="user",
            smtp_password="pw",
        ),
    )
    fake_server = mocker.MagicMock()
    mocker.patch(
        "app.services.email_service.smtplib.SMTP"
    ).return_value.__enter__.return_value = fake_server

    success = await send_password_reset_email("jane@example.com", "Jane", "123456")

    assert success is True
    fake_server.sendmail.assert_called_once()


async def test_send_verification_email_local_dev_without_smtp(
    mocker: MockerFixture,
) -> None:
    mocker.patch(
        "app.services.email_service.get_smtp_settings",
        return_value=SMTPSettings(),
    )

    success = await send_verification_email("jane@example.com", "Jane", "123456")
    assert success is True


async def test_send_verification_email_via_smtp_success(mocker: MockerFixture) -> None:
    mocker.patch(
        "app.services.email_service.get_smtp_settings",
        return_value=SMTPSettings(
            smtp_host="smtp.example.com",
            smtp_user="user",
            smtp_password="pw",
        ),
    )
    fake_server = mocker.MagicMock()
    mocker.patch(
        "app.services.email_service.smtplib.SMTP"
    ).return_value.__enter__.return_value = fake_server

    success = await send_verification_email("jane@example.com", "Jane", "123456")

    assert success is True
    fake_server.starttls.assert_called_once()
    fake_server.login.assert_called_once_with("user", "pw")
    fake_server.sendmail.assert_called_once()


async def test_send_verification_email_via_smtp_failure_returns_false(
    mocker: MockerFixture,
) -> None:
    mocker.patch(
        "app.services.email_service.get_smtp_settings",
        return_value=SMTPSettings(
            smtp_host="smtp.example.com",
            smtp_user="user",
            smtp_password="pw",
        ),
    )
    mocker.patch(
        "app.services.email_service.smtplib.SMTP",
        side_effect=smtplib.SMTPException("boom"),
    )

    success = await send_verification_email("jane@example.com", "Jane", "123456")
    assert success is False
