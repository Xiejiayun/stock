"""Authentication and whitelist helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from typing import Any

import requests
from fastapi import Header, HTTPException, status


GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "28800"))


@dataclass(frozen=True)
class CurrentUser:
    email: str
    name: str = ""
    picture: str = ""
    provider: str = "google"


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def get_google_client_id() -> str:
    return os.getenv("GOOGLE_CLIENT_ID", "").strip()


def get_allowed_emails() -> set[str]:
    return {email.lower() for email in _split_csv(os.getenv("ALLOWED_EMAILS", ""))}


def get_session_secret() -> str:
    secret = os.getenv("SESSION_SECRET", "").strip()
    if secret:
        return secret
    # Development fallback keeps local startup simple. Configure SESSION_SECRET in Azure.
    return "dev-session-secret-change-me"


def auth_config() -> dict[str, Any]:
    return {
        "google_client_id": get_google_client_id(),
        "google_enabled": bool(get_google_client_id()),
        "whitelist_configured": bool(get_allowed_emails()),
        "dev_login_enabled": os.getenv("DEV_LOGIN_ENABLED", "false").lower() == "true",
    }


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _sign(message: str) -> str:
    return _b64url_encode(
        hmac.new(get_session_secret().encode("utf-8"), message.encode("utf-8"), hashlib.sha256).digest()
    )


def create_session_token(user: CurrentUser) -> str:
    now = int(time.time())
    payload = {
        "email": user.email.lower(),
        "name": user.name,
        "picture": user.picture,
        "provider": user.provider,
        "iat": now,
        "exp": now + SESSION_TTL_SECONDS,
    }
    encoded = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    return f"{encoded}.{_sign(encoded)}"


def verify_session_token(token: str) -> CurrentUser:
    try:
        encoded, signature = token.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录会话无效") from exc

    if not hmac.compare_digest(signature, _sign(encoded)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录会话签名无效")

    try:
        payload = json.loads(_b64url_decode(encoded))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录会话解析失败") from exc

    if int(payload.get("exp", 0)) < int(time.time()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录会话已过期")

    email = str(payload.get("email", "")).lower()
    if not is_allowed_email(email):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号不在白名单中")

    return CurrentUser(
        email=email,
        name=str(payload.get("name", "")),
        picture=str(payload.get("picture", "")),
        provider=str(payload.get("provider", "google")),
    )


def is_allowed_email(email: str) -> bool:
    allowed = get_allowed_emails()
    return bool(email) and email.lower() in allowed


def verify_google_id_token(credential: str) -> CurrentUser:
    client_id = get_google_client_id()
    if not client_id:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Google 登录尚未配置")

    try:
        response = requests.get(GOOGLE_TOKENINFO_URL, params={"id_token": credential}, timeout=5)
    except requests.RequestException as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Google 登录校验服务暂不可用") from exc

    if response.status_code != 200:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google 登录凭证无效")

    payload = response.json()
    if payload.get("aud") != client_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google 登录客户端不匹配")

    if payload.get("email_verified") not in (True, "true", "True", "1"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google 邮箱未验证")

    email = str(payload.get("email", "")).lower()
    if not is_allowed_email(email):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号不在白名单中")

    return CurrentUser(
        email=email,
        name=str(payload.get("name", "")),
        picture=str(payload.get("picture", "")),
        provider="google",
    )


def create_dev_session(email: str) -> CurrentUser:
    if os.getenv("DEV_LOGIN_ENABLED", "false").lower() != "true":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="开发登录未启用")
    email = email.lower().strip()
    if not is_allowed_email(email):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号不在白名单中")
    return CurrentUser(email=email, name=email, provider="dev")


def require_user(authorization: str | None = Header(default=None)) -> CurrentUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")
    return verify_session_token(authorization.removeprefix("Bearer ").strip())
