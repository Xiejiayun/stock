#!/usr/bin/env python3
"""Verify the deployed Stock app contract after Azure deployment."""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass
class HttpResult:
    status: int
    body: str


def request_json(url: str, expected_status: int = 200, timeout: int = 20) -> dict[str, Any]:
    result = request_text(url, expected_status=expected_status, timeout=timeout)
    try:
        return json.loads(result.body)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"{url} did not return JSON: {result.body[:200]}") from exc


def request_text(url: str, expected_status: int = 200, timeout: int = 20) -> HttpResult:
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            status = response.status
            body = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        status = exc.code
        body = exc.read().decode("utf-8", errors="replace")
    except URLError as exc:
        raise AssertionError(f"Unable to reach {url}: {exc}") from exc

    if status != expected_status:
        raise AssertionError(f"{url} returned {status}, expected {expected_status}. Body: {body[:500]}")
    return HttpResult(status=status, body=body)


def wait_for_health(base_url: str, attempts: int, delay_seconds: int) -> None:
    health_url = f"{base_url}/api/health"
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            payload = request_json(health_url)
            if payload.get("status") == "ok":
                print(f"health ok: {health_url}")
                return
            raise AssertionError(f"Unexpected health payload: {payload}")
        except Exception as exc:  # noqa: BLE001 - retry boundary for cold starts.
            last_error = exc
            time.sleep(delay_seconds)
    raise AssertionError(f"Health check did not pass after {attempts} attempts: {last_error}")


def verify_contract(base_url: str, require_auth_settings: bool) -> None:
    config = request_json(f"{base_url}/api/auth/config")
    if config.get("code") != 0 or not isinstance(config.get("data"), dict):
        raise AssertionError(f"Unexpected auth config payload: {config}")

    auth_data = config["data"]
    required_config_keys = {"google_client_id", "google_enabled", "whitelist_configured", "dev_login_enabled"}
    missing_keys = required_config_keys - set(auth_data)
    if missing_keys:
        raise AssertionError(f"Auth config missing keys: {sorted(missing_keys)}")

    if require_auth_settings:
        if not auth_data.get("google_enabled"):
            raise AssertionError("GOOGLE_CLIENT_ID is configured in CI secrets but deployed app reports google_enabled=false")
        if not auth_data.get("whitelist_configured"):
            raise AssertionError("ALLOWED_EMAILS is configured in CI secrets but deployed app reports whitelist_configured=false")

    unauth_quant = request_json(f"{base_url}/api/quant/requirements", expected_status=401)
    if unauth_quant.get("detail") != "请先登录":
        raise AssertionError(f"Protected quant endpoint returned unexpected 401 body: {unauth_quant}")

    openapi = request_json(f"{base_url}/openapi.json")
    paths = set(openapi.get("paths", {}))
    expected_paths = {
        "/api/auth/config",
        "/api/auth/google",
        "/api/auth/me",
        "/api/quant/requirements",
        "/api/quant/{symbol}/analysis",
        "/api/market/overview",
    }
    missing_paths = expected_paths - paths
    if missing_paths:
        raise AssertionError(f"OpenAPI schema missing paths: {sorted(missing_paths)}")

    print("deployment contract ok")
    print(
        "auth settings: "
        f"google_enabled={auth_data['google_enabled']}, "
        f"whitelist_configured={auth_data['whitelist_configured']}, "
        f"dev_login_enabled={auth_data['dev_login_enabled']}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("base_url", help="Base URL, for example https://stock.azurewebsites.net")
    parser.add_argument("--attempts", type=int, default=30)
    parser.add_argument("--delay-seconds", type=int, default=10)
    parser.add_argument("--require-auth-settings", action="store_true")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    try:
        wait_for_health(base_url, attempts=args.attempts, delay_seconds=args.delay_seconds)
        verify_contract(base_url, require_auth_settings=args.require_auth_settings)
    except AssertionError as exc:
        print(f"verification failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
