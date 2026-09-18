import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import structlog
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.constants.auth import OTP_EXPIRY_MINUTES, PASSWORD_RESET_EXPIRY_MINUTES
from app.core.config import get_smtp_settings

logger = structlog.get_logger(__name__)


_EMAIL_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "email"
_jinja_env = Environment(
    loader=FileSystemLoader(_EMAIL_TEMPLATES_DIR),
    autoescape=select_autoescape(["html"]),
)


def render_otp_email_html(name: str, otp_code: str) -> str:
    template = _jinja_env.get_template("otp_verification.html")
    return template.render(
        name=name or "there",
        otp_digits=otp_code.strip(),
        expiry_minutes=OTP_EXPIRY_MINUTES,
    )


def render_password_reset_email_html(name: str, otp_code: str) -> str:
    template = _jinja_env.get_template("password_reset.html")
    return template.render(
        name=name or "there",
        otp_digits=otp_code.strip(),
        expiry_minutes=PASSWORD_RESET_EXPIRY_MINUTES,
    )


def _send_via_smtp_sync(
    *,
    host: str,
    port: int,
    user: str,
    password: str,
    from_addr: str,
    to_email: str,
    subject: str,
    plain_text: str,
    html_content: str,
) -> None:
    """Blocking SMTP handshake (connect/STARTTLS/login/send) - runs the
    real network I/O, so it's always dispatched via asyncio.to_thread()
    rather than awaited directly, to avoid stalling the event loop for
    every other concurrent request during the handshake.
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Prepwise <{from_addr}>"
    msg["To"] = to_email

    msg.attach(MIMEText(plain_text, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        server.sendmail(from_addr, [to_email], msg.as_string())


async def _send_email(
    *, to_email: str, subject: str, plain_text: str, html_content: str, log_slug: str
) -> bool:
    """Shared SMTP-sending path for every outbound auth email - both
    send_verification_email() and send_password_reset_email() build their
    own subject/body text, then hand off here so the actual SMTP
    connection handling (and its local-dev-without-SMTP fallback) exists
    in exactly one place.
    """
    settings = get_smtp_settings()

    if settings.smtp_host and settings.smtp_user and settings.smtp_password:
        try:
            await asyncio.to_thread(
                _send_via_smtp_sync,
                host=settings.smtp_host,
                port=settings.smtp_port,
                user=settings.smtp_user,
                password=settings.smtp_password,
                from_addr=settings.smtp_from,
                to_email=to_email,
                subject=subject,
                plain_text=plain_text,
                html_content=html_content,
            )
            logger.info(f"smtp_{log_slug}_email_sent", email=to_email)
            return True
        except (smtplib.SMTPException, OSError):
            logger.exception(f"smtp_{log_slug}_email_failed", email=to_email)
            return False

    # No SMTP configured (local dev) - the OTP is only ever logged here,
    # never returned in an API response.
    logger.info(f"local_dev_{log_slug}_email_logged", email=to_email)
    return True


def _plain_text_safe_name(name: str) -> str:
    return name.replace("\r", " ").replace("\n", " ")


async def send_verification_email(email: str, name: str, otp_code: str) -> bool:
    logger.info("send_verification_email_invoked", email=email)
    safe_name = _plain_text_safe_name(name)
    plain_text = (
        f"Hi {safe_name},\n\nYour Prepwise verification code is: {otp_code}\n\n"
        f"This code will expire in {OTP_EXPIRY_MINUTES} minutes.\n\nPrepwise Inc."
    )
    return await _send_email(
        to_email=email,
        subject="Your Prepwise verification code",
        plain_text=plain_text,
        html_content=render_otp_email_html(name, otp_code),
        log_slug="verification",
    )


async def send_password_reset_email(email: str, name: str, otp_code: str) -> bool:
    logger.info("send_password_reset_email_invoked", email=email)
    safe_name = _plain_text_safe_name(name)
    plain_text = (
        f"Hi {safe_name},\n\nYour Prepwise password reset code is: {otp_code}\n\n"
        f"This code will expire in {PASSWORD_RESET_EXPIRY_MINUTES} minutes.\n\n"
        "If you didn't request this, you can safely ignore this email.\n\nPrepwise Inc."
    )
    return await _send_email(
        to_email=email,
        subject="Your Prepwise password reset code",
        plain_text=plain_text,
        html_content=render_password_reset_email_html(name, otp_code),
        log_slug="password_reset",
    )
