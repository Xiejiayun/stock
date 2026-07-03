import base64
import json
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import auth_service
from auth_service import CurrentUser, create_session_token, verify_google_id_token, verify_session_token
from main import app


@pytest.fixture(autouse=True)
def auth_env(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client.apps.googleusercontent.com")
    monkeypatch.setenv("ALLOWED_EMAILS", "allowed@example.com,second@example.com")
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret-32-characters")
    monkeypatch.setenv("DEV_LOGIN_ENABLED", "false")


def test_session_token_roundtrip_for_whitelisted_user():
    token = create_session_token(CurrentUser(email="Allowed@Example.com", name="Allowed User"))

    user = verify_session_token(token)

    assert user.email == "allowed@example.com"
    assert user.name == "Allowed User"


def test_session_token_rejects_tampered_payload():
    token = create_session_token(CurrentUser(email="allowed@example.com"))
    encoded, signature = token.split(".", 1)
    payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
    payload["email"] = "attacker@example.com"
    tampered = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")

    with pytest.raises(HTTPException) as exc_info:
        verify_session_token(f"{tampered}.{signature}")

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "登录会话签名无效"


def test_session_token_rechecks_current_whitelist(monkeypatch):
    token = create_session_token(CurrentUser(email="allowed@example.com"))
    monkeypatch.setenv("ALLOWED_EMAILS", "second@example.com")

    with pytest.raises(HTTPException) as exc_info:
        verify_session_token(token)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "账号不在白名单中"


def test_expired_session_token_is_rejected(monkeypatch):
    monkeypatch.setattr(auth_service, "SESSION_TTL_SECONDS", -1)
    token = create_session_token(CurrentUser(email="allowed@example.com"))

    with pytest.raises(HTTPException) as exc_info:
        verify_session_token(token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "登录会话已过期"


class FakeGoogleResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def test_google_login_requires_configured_client(monkeypatch):
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)

    with pytest.raises(HTTPException) as exc_info:
        verify_google_id_token("credential")

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Google 登录尚未配置"


def test_google_login_accepts_verified_whitelisted_email(monkeypatch):
    def fake_get(url, params, timeout):
        assert url == auth_service.GOOGLE_TOKENINFO_URL
        assert params == {"id_token": "credential"}
        assert timeout == 5
        return FakeGoogleResponse(
            200,
            {
                "aud": "client.apps.googleusercontent.com",
                "email": "Allowed@Example.com",
                "email_verified": "true",
                "name": "Allowed User",
                "picture": "https://example.com/avatar.png",
            },
        )

    monkeypatch.setattr(auth_service.requests, "get", fake_get)

    user = verify_google_id_token("credential")

    assert user.email == "allowed@example.com"
    assert user.name == "Allowed User"
    assert user.provider == "google"


def test_google_login_rejects_non_whitelisted_email(monkeypatch):
    monkeypatch.setattr(
        auth_service.requests,
        "get",
        lambda *args, **kwargs: FakeGoogleResponse(
            200,
            {
                "aud": "client.apps.googleusercontent.com",
                "email": "other@example.com",
                "email_verified": True,
            },
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        verify_google_id_token("credential")

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "账号不在白名单中"


def test_google_login_rejects_wrong_audience(monkeypatch):
    monkeypatch.setattr(
        auth_service.requests,
        "get",
        lambda *args, **kwargs: FakeGoogleResponse(
            200,
            {
                "aud": "wrong-client.apps.googleusercontent.com",
                "email": "allowed@example.com",
                "email_verified": True,
            },
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        verify_google_id_token("credential")

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Google 登录客户端不匹配"


def test_protected_quant_endpoint_requires_bearer_token():
    client = TestClient(app)

    response = client.get("/api/quant/requirements")

    assert response.status_code == 401
    assert response.json() == {"detail": "请先登录"}


def test_dev_login_is_disabled_by_default():
    client = TestClient(app)

    response = client.post("/api/auth/dev", json={"email": "allowed@example.com"})

    assert response.status_code == 404
    assert response.json() == {"detail": "开发登录未启用"}


def test_dev_login_issues_token_for_whitelisted_email(monkeypatch):
    monkeypatch.setenv("DEV_LOGIN_ENABLED", "true")
    client = TestClient(app)

    login = client.post("/api/auth/dev", json={"email": "Allowed@Example.com"})

    assert login.status_code == 200
    body = login.json()
    token = body["data"]["token"]
    assert body["data"]["user"]["email"] == "allowed@example.com"
    assert body["data"]["user"]["provider"] == "dev"

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["data"]["email"] == "allowed@example.com"


def test_dev_login_rejects_non_whitelisted_email(monkeypatch):
    monkeypatch.setenv("DEV_LOGIN_ENABLED", "true")
    client = TestClient(app)

    response = client.post("/api/auth/dev", json={"email": "other@example.com"})

    assert response.status_code == 403
    assert response.json() == {"detail": "账号不在白名单中"}
