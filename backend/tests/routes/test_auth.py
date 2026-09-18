from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.constants.app import API_V1_PREFIX
from app.core.security import create_access_token
from app.models.user import User


def _fake_user(**overrides) -> User:
    defaults = {
        "id": "usr_abc123",
        "email": "jane@example.com",
        "name": "Jane Doe",
        "auth_provider": "email",
        "is_verified": True,
        "token_version": 0,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return User(**defaults)


def test_google_auth_success(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def mock_verify(credential: str):
        return {
            "sub": "google-sub-999888",
            "email": "googleuser@example.com",
            "name": "Google User",
            "picture": "https://lh3.googleusercontent.com/avatar.jpg",
        }

    monkeypatch.setattr("app.services.auth_service.verify_google_token", mock_verify)

    fake_user = _fake_user(
        id="usr_google-sub-999888",
        google_id="google-sub-999888",
        email="googleuser@example.com",
        name="Google User",
        picture="https://lh3.googleusercontent.com/avatar.jpg",
        auth_provider="google",
    )

    async def mock_auth_user(*args, **kwargs):
        return fake_user

    monkeypatch.setattr(
        "app.services.auth_service.authenticate_or_create_google_user", mock_auth_user
    )

    response = client.post(
        f"{API_V1_PREFIX}/auth/google",
        json={"credential": "sample-google-id-token"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["user"]["email"] == "googleuser@example.com"
    assert data["data"]["user"]["name"] == "Google User"
    assert data["data"]["token"]


def test_google_auth_invalid_token_returns_401(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services.auth_service import GoogleTokenInvalidError

    async def mock_verify(credential: str):
        raise GoogleTokenInvalidError("Invalid or expired Google authentication token.")

    monkeypatch.setattr("app.services.auth_service.verify_google_token", mock_verify)

    response = client.post(
        f"{API_V1_PREFIX}/auth/google", json={"credential": "bad-token"}
    )

    assert response.status_code == 401
    assert response.json()["success"] is False


def test_google_auth_provider_unreachable_returns_502(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services.auth_service import GoogleAuthProviderError

    async def mock_verify(credential: str):
        raise GoogleAuthProviderError(
            "Unable to communicate with Google authentication servers."
        )

    monkeypatch.setattr("app.services.auth_service.verify_google_token", mock_verify)

    response = client.post(
        f"{API_V1_PREFIX}/auth/google", json={"credential": "whatever"}
    )

    assert response.status_code == 502


def test_google_auth_existing_email_requires_linking_returns_409(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services.auth_service import GoogleAccountLinkingRequiredError

    async def mock_verify(credential: str):
        return {
            "sub": "google-sub-1",
            "email": "taken@example.com",
            "name": "Someone",
            "picture": None,
        }

    async def mock_auth_user(*args, **kwargs):
        raise GoogleAccountLinkingRequiredError(
            "An account with this email address already exists."
        )

    monkeypatch.setattr("app.services.auth_service.verify_google_token", mock_verify)
    monkeypatch.setattr(
        "app.services.auth_service.authenticate_or_create_google_user", mock_auth_user
    )

    response = client.post(
        f"{API_V1_PREFIX}/auth/google", json={"credential": "some-real-token"}
    )

    assert response.status_code == 409
    assert response.json()["success"] is False


def test_register_existing_verified_email_returns_400(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services.auth_service import EmailAlreadyRegisteredError

    async def mock_create_pending(*args, **kwargs):
        raise EmailAlreadyRegisteredError(
            "An account with this email address already exists. Please sign in."
        )

    monkeypatch.setattr(
        "app.services.auth_service.create_pending_registration", mock_create_pending
    )

    response = client.post(
        f"{API_V1_PREFIX}/auth/register",
        json={
            "name": "Jane Doe",
            "email": "jane@example.com",
            "password": "Prepwise#2026",
        },
    )

    assert response.status_code == 400


def test_register_weak_password_fails(client: TestClient) -> None:
    response = client.post(
        f"{API_V1_PREFIX}/auth/register",
        json={"name": "Weak User", "email": "weak@example.com", "password": "weak"},
    )
    assert response.status_code == 422


def test_register_success_never_echoes_otp(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def mock_create_pending(*args, **kwargs):
        return "jane@example.com", "654321"

    monkeypatch.setattr(
        "app.services.auth_service.create_pending_registration", mock_create_pending
    )

    response = client.post(
        f"{API_V1_PREFIX}/auth/register",
        json={
            "name": "Jane Doe",
            "email": "jane@example.com",
            "password": "Prepwise#2026",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["otp_sent"] is True
    assert data["data"]["email"] == "jane@example.com"
    assert "dev_otp" not in data["data"]


@pytest.mark.parametrize(
    "exception_name,expected_status",
    [
        ("PendingRegistrationNotFoundError", 400),
        ("OtpExpiredError", 400),
        ("IncorrectOtpError", 400),
    ],
)
def test_verify_otp_error_branches(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    exception_name: str,
    expected_status: int,
) -> None:
    from app.services import auth_service

    exception_cls = getattr(auth_service, exception_name)

    async def mock_verify_otp(*args, **kwargs):
        raise exception_cls("failed")

    monkeypatch.setattr(
        "app.services.auth_service.verify_otp_and_create_user", mock_verify_otp
    )

    response = client.post(
        f"{API_V1_PREFIX}/auth/verify-otp",
        json={"email": "jane@example.com", "otp": "000000"},
    )

    assert response.status_code == expected_status


def test_resend_otp_no_pending_record_returns_400(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services.auth_service import PendingRegistrationNotFoundError

    async def mock_resend(*args, **kwargs):
        raise PendingRegistrationNotFoundError(
            "No pending registration found for this email address."
        )

    monkeypatch.setattr(
        "app.services.auth_service.resend_registration_otp", mock_resend
    )

    response = client.post(
        f"{API_V1_PREFIX}/auth/resend-otp", json={"email": "jane@example.com"}
    )

    assert response.status_code == 400


def test_verify_otp_success(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_user = _fake_user()

    async def mock_verify_otp(*args, **kwargs):
        return fake_user

    monkeypatch.setattr(
        "app.services.auth_service.verify_otp_and_create_user", mock_verify_otp
    )

    response = client.post(
        f"{API_V1_PREFIX}/auth/verify-otp",
        json={"email": "jane@example.com", "otp": "654321"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["user"]["email"] == "jane@example.com"
    assert data["data"]["user"]["is_verified"] is True


def test_resend_otp_success(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def mock_resend(*args, **kwargs):
        return "987654"

    monkeypatch.setattr(
        "app.services.auth_service.resend_registration_otp", mock_resend
    )

    response = client.post(
        f"{API_V1_PREFIX}/auth/resend-otp",
        json={"email": "jane@example.com"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["otp_sent"] is True


def test_login_success(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_user = _fake_user()

    async def mock_auth_email(*args, **kwargs):
        return fake_user

    monkeypatch.setattr(
        "app.services.auth_service.authenticate_email_user", mock_auth_email
    )

    response = client.post(
        f"{API_V1_PREFIX}/auth/login",
        json={"email": "jane@example.com", "password": "Prepwise#2026"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["user"]["email"] == "jane@example.com"


def test_login_invalid_credentials_returns_401(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services.auth_service import InvalidCredentialsError

    async def mock_auth_email(*args, **kwargs):
        raise InvalidCredentialsError("Invalid email or password.")

    monkeypatch.setattr(
        "app.services.auth_service.authenticate_email_user", mock_auth_email
    )

    response = client.post(
        f"{API_V1_PREFIX}/auth/login",
        json={"email": "jane@example.com", "password": "wrong"},
    )

    assert response.status_code == 401
    assert response.json()["success"] is False


def test_login_unverified_email_returns_403(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services.auth_service import EmailNotVerifiedError

    async def mock_auth_email(*args, **kwargs):
        raise EmailNotVerifiedError(
            "Please verify your email address before signing in."
        )

    monkeypatch.setattr(
        "app.services.auth_service.authenticate_email_user", mock_auth_email
    )

    response = client.post(
        f"{API_V1_PREFIX}/auth/login",
        json={"email": "jane@example.com", "password": "Prepwise#2026"},
    )

    assert response.status_code == 403


def test_forgot_password_returns_generic_message(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def mock_request_reset(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "app.services.auth_service.request_password_reset", mock_request_reset
    )

    response = client.post(
        f"{API_V1_PREFIX}/auth/forgot-password", json={"email": "nobody@example.com"}
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert "If an account exists" in data["message"]
    assert "dev_otp" not in data


def test_forgot_password_never_echoes_otp_even_when_account_exists(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def mock_request_reset(*args, **kwargs):
        return "654321"

    monkeypatch.setattr(
        "app.services.auth_service.request_password_reset", mock_request_reset
    )

    response = client.post(
        f"{API_V1_PREFIX}/auth/forgot-password", json={"email": "jane@example.com"}
    )

    assert response.status_code == 200
    assert "dev_otp" not in response.json()["data"]


def test_verify_reset_code_invalid_returns_400(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services.auth_service import InvalidOrExpiredResetCodeError

    async def mock_verify(*args, **kwargs):
        raise InvalidOrExpiredResetCodeError("Invalid or expired reset code.")

    monkeypatch.setattr("app.services.auth_service.verify_reset_code", mock_verify)

    response = client.post(
        f"{API_V1_PREFIX}/auth/verify-reset-code",
        json={"email": "jane@example.com", "otp": "000000"},
    )

    assert response.status_code == 400


def test_verify_reset_code_success_returns_reset_token(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def mock_verify(*args, **kwargs):
        return "a-reset-token"

    monkeypatch.setattr("app.services.auth_service.verify_reset_code", mock_verify)

    response = client.post(
        f"{API_V1_PREFIX}/auth/verify-reset-code",
        json={"email": "jane@example.com", "otp": "123456"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["reset_token"] == "a-reset-token"


def test_reset_password_invalid_token_returns_401(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services.auth_service import PasswordResetTokenInvalidError

    async def mock_reset(*args, **kwargs):
        raise PasswordResetTokenInvalidError("Invalid or expired reset token.")

    monkeypatch.setattr("app.services.auth_service.reset_password", mock_reset)

    response = client.post(
        f"{API_V1_PREFIX}/auth/reset-password",
        json={"reset_token": "bad-token", "new_password": "NewPassword#2026"},
    )

    assert response.status_code == 401


def test_reset_password_weak_password_returns_422(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services.auth_service import WeakPasswordError

    async def mock_reset(*args, **kwargs):
        raise WeakPasswordError("Password must contain at least one number.")

    monkeypatch.setattr("app.services.auth_service.reset_password", mock_reset)

    response = client.post(
        f"{API_V1_PREFIX}/auth/reset-password",
        json={"reset_token": "a-token", "new_password": "NoNumberHere#"},
    )

    assert response.status_code == 422


def test_reset_password_success(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def mock_reset(*args, **kwargs):
        return None

    monkeypatch.setattr("app.services.auth_service.reset_password", mock_reset)

    response = client.post(
        f"{API_V1_PREFIX}/auth/reset-password",
        json={"reset_token": "a-token", "new_password": "NewPassword#2026"},
    )

    assert response.status_code == 200
    assert response.json()["success"] is True


def test_get_me_with_valid_token(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_user = _fake_user()

    async def mock_get_user_by_id(*args, **kwargs):
        return fake_user

    monkeypatch.setattr("app.services.auth_service.get_user_by_id", mock_get_user_by_id)
    token = create_access_token(fake_user.id, fake_user.token_version)

    response = client.get(
        f"{API_V1_PREFIX}/auth/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json()["data"]["user"]["email"] == "jane@example.com"


def test_get_me_without_authorization_header_returns_401(client: TestClient) -> None:
    response = client.get(f"{API_V1_PREFIX}/auth/me")

    assert response.status_code == 401
    assert response.json()["success"] is False


def test_get_me_with_invalid_token_returns_401(client: TestClient) -> None:
    response = client.get(
        f"{API_V1_PREFIX}/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )

    assert response.status_code == 401
    assert response.json()["success"] is False


def test_get_me_with_token_from_before_a_password_reset_returns_401(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Token issued at token_version=0, but the user's row has since moved
    # to token_version=1 (e.g. a password reset) - must be rejected.
    fake_user = _fake_user(token_version=1)

    async def mock_get_user_by_id(*args, **kwargs):
        return fake_user

    monkeypatch.setattr("app.services.auth_service.get_user_by_id", mock_get_user_by_id)
    stale_token = create_access_token(fake_user.id, 0)

    response = client.get(
        f"{API_V1_PREFIX}/auth/me", headers={"Authorization": f"Bearer {stale_token}"}
    )

    assert response.status_code == 401
    assert response.json()["success"] is False


def test_get_me_with_token_for_deleted_user_returns_401(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def mock_get_user_by_id(*args, **kwargs):
        return None

    monkeypatch.setattr("app.services.auth_service.get_user_by_id", mock_get_user_by_id)
    token = create_access_token("usr_no_longer_exists", 0)

    response = client.get(
        f"{API_V1_PREFIX}/auth/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 401
    assert response.json()["success"] is False
