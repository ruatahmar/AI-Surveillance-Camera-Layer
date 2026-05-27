import os
import smtplib
import logging
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import EmailConfig

logger = logging.getLogger(__name__)

ALERT_LABEL_MAP = {
    "no_id": "alert_no_id",
    "wrong_lanyard": "alert_wrong_lanyard",
    "green_lanyard": "alert_green_lanyard",
    "loitering": "alert_loitering",
    "crowd": "alert_crowd",
}


def _env_str(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ[key])
    except (KeyError, ValueError):
        return default


def _env_bool(key: str, default: bool) -> bool:
    val = os.environ.get(key)
    if val is None:
        return default
    return val.lower() in ("1", "true", "yes")


def should_send_email(cfg: EmailConfig, alert_type: str) -> bool:
    if not cfg.enabled:
        return False
    field = ALERT_LABEL_MAP.get(alert_type)
    if field is None:
        return False
    return getattr(cfg, field, False)


def send_alert_email(
    cfg: EmailConfig,
    camera_name: str,
    alert_type: str,
) -> None:
    if not cfg.enabled:
        return
    if not cfg.to_addrs:
        logger.warning("No recipients configured, skipping email")
        return

    smtp_host = _env_str("SMTP_HOST")
    smtp_port = _env_int("SMTP_PORT", 587)
    smtp_user = _env_str("SMTP_USER")
    smtp_password = _env_str("SMTP_PASSWORD")
    smtp_from = _env_str("SMTP_FROM", smtp_user)
    smtp_use_tls = _env_bool("SMTP_USE_TLS", True)

    if not smtp_password:
        logger.warning("SMTP_PASSWORD not set, skipping email")
        return
    if not smtp_user:
        logger.warning("SMTP_USER not set, skipping email")
        return

    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    subject = f"[AI Surveillance] {alert_type.replace('_', ' ').title()} — {camera_name}"
    body = (
        f"Camera: {camera_name}\n"
        f"Alert: {alert_type}\n"
        f"Time: {ts}\n"
    )

    msg = MIMEMultipart()
    msg["From"] = smtp_from
    msg["To"] = ", ".join(cfg.to_addrs)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(smtp_host, smtp_port)
        if smtp_use_tls:
            server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        logger.info("Email sent for %s alert on %s", alert_type, camera_name)
    except Exception:
        logger.exception("Failed to send email alert for %s on %s", alert_type, camera_name)
