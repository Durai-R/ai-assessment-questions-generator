from datetime import datetime, timedelta, timezone
from http.cookies import SimpleCookie
from types import SimpleNamespace

import httpx
import jwt
import pytest
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.config import Settings
from app.main import create_app


ORIGIN = "http://localhost:5173"
TRUSTED_ORIGIN = "http://localhost:3000"
SECRET = "test-only-secret-that-is-at-least-thirty-two-characters"
PASSWORD = "assessment-password-123"
COOKIE_NAME = "assessment_access_token"


class FakeUsers:
    def __init__(self) -> None:
        self.by_id = {}
        self.by_email = {}

    async def find_one(self, query: dict) -> dict | None:
        if "_id" in query:
            return self.by_id.get(query["_id"])
        return self.by_email.get(query.get("email"))

    async def insert_one(self, document: dict):
        if document["email"] in self.by_email:
            raise DuplicateKeyError("duplicate email")
        user_id = ObjectId()
        user = {**document, "_id": user_id}
        self.by_id[user_id] = user
        self.by_email[document["email"]] = user
        return SimpleNamespace(inserted_id=user_id)


def make_test_app(
    *,
    auth_cookie_secure: bool | None = False,
    trusted_origins: str = "",
    environment: str = "development",
):
    users = FakeUsers()
    settings = Settings(
        jwt_secret=SECRET,
        frontend_origin=ORIGIN,
        trusted_origins=trusted_origins,
        jwt_expiry_minutes=5,
        auth_cookie_secure=auth_cookie_secure,
        environment=environment,
    )
    return create_app(settings, database=SimpleNamespace(users=users))


@pytest.mark.asyncio
async def test_register_login_cookie_me_logout_and_jwt_validation():
    application = make_test_app()
    transport = httpx.ASGITransport(app=application, raise_app_exceptions=False)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Origin": ORIGIN},
    ) as client:
        registered = await client.post(
            "/api/auth/register",
            json={"email": " Person@Example.com ", "password": PASSWORD},
        )
        assert registered.status_code == 201
        assert registered.json()["email"] == "person@example.com"
        assert "password_hash" not in registered.text

        duplicate = await client.post(
            "/api/auth/register",
            json={"email": "person@example.com", "password": PASSWORD},
        )
        assert duplicate.status_code == 409

        wrong_password = await client.post(
            "/api/auth/login",
            json={"email": "person@example.com", "password": "wrong-password-123"},
        )
        unknown_email = await client.post(
            "/api/auth/login",
            json={"email": "missing@example.com", "password": "wrong-password-123"},
        )
        assert wrong_password.status_code == unknown_email.status_code == 401
        assert wrong_password.json() == unknown_email.json()
        assert "set-cookie" not in wrong_password.headers

        login = await client.post(
            "/api/auth/login",
            json={"email": "PERSON@example.com", "password": PASSWORD},
        )
        assert login.status_code == 200
        assert login.json() == registered.json()
        assert "access_token" not in login.json()

        cookie = SimpleCookie()
        cookie.load(login.headers["set-cookie"])
        token_cookie = cookie[COOKIE_NAME]
        assert token_cookie["httponly"]
        assert token_cookie["path"] == "/"
        assert token_cookie["samesite"].lower() == "lax"
        assert token_cookie["max-age"] == "300"
        assert not token_cookie["secure"]

        token = client.cookies.get(COOKIE_NAME)
        claims = jwt.decode(token, SECRET, algorithms=["HS256"])
        assert claims["sub"] == registered.json()["id"]
        assert claims["exp"] > datetime.now(timezone.utc).timestamp()
        assert (await client.get("/api/auth/me")).json() == registered.json()

        client.cookies.clear()
        missing_cookie = await client.get("/api/auth/me")
        assert missing_cookie.status_code == 401
        assert "www-authenticate" not in missing_cookie.headers

        client.cookies.set(COOKIE_NAME, token + "tampered", domain="test.local", path="/")
        tampered = await client.get("/api/auth/me")
        assert tampered.status_code == 401

        expired = jwt.encode(
            {
                "sub": registered.json()["id"],
                "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
            },
            SECRET,
            algorithm="HS256",
        )
        client.cookies.set(COOKIE_NAME, expired, domain="test.local", path="/")
        expired_response = await client.get("/api/auth/me")
        assert expired_response.status_code == 401

        missing_user = jwt.encode(
            {"sub": str(ObjectId()), "exp": datetime.now(timezone.utc) + timedelta(minutes=1)},
            SECRET,
            algorithm="HS256",
        )
        client.cookies.set(COOKIE_NAME, missing_user, domain="test.local", path="/")
        missing_user_response = await client.get("/api/auth/me")
        assert missing_user_response.status_code == 401

        client.cookies.set(COOKIE_NAME, token, domain="test.local", path="/")
        logout = await client.post("/api/auth/logout")
        assert logout.status_code == 204
        deleted_cookie = logout.headers["set-cookie"].lower()
        assert "max-age=0" in deleted_cookie
        assert "path=/" in deleted_cookie
        assert "httponly" in deleted_cookie
        assert "samesite=lax" in deleted_cookie
        assert (await client.get("/api/auth/me")).status_code == 401


@pytest.mark.asyncio
async def test_secure_cookie_can_be_enabled_for_https():
    application = make_test_app(auth_cookie_secure=False, environment="production")
    transport = httpx.ASGITransport(app=application, raise_app_exceptions=False)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Origin": ORIGIN},
    ) as client:
        await client.post(
            "/api/auth/register",
            json={"email": "secure@example.com", "password": PASSWORD},
        )
        login = await client.post(
            "/api/auth/login",
            json={"email": "secure@example.com", "password": PASSWORD},
        )
        cookie = SimpleCookie()
        cookie.load(login.headers["set-cookie"])
        assert cookie[COOKIE_NAME]["secure"]


@pytest.mark.asyncio
async def test_state_changing_auth_routes_reject_missing_and_untrusted_origins():
    application = make_test_app(trusted_origins=TRUSTED_ORIGIN)
    transport = httpx.ASGITransport(app=application, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        for origin in (None, "http://untrusted.example"):
            headers = {"Origin": origin} if origin else {}
            for path, method, json_body in (
                ("/api/auth/register", "POST", {"email": "user@example.com", "password": PASSWORD}),
                ("/api/auth/login", "POST", {"email": "user@example.com", "password": PASSWORD}),
                ("/api/auth/logout", "POST", None),
            ):
                response = await client.request(method, path, headers=headers, json=json_body)
                assert response.status_code == 403

        trusted_register = await client.post(
            "/api/auth/register",
            headers={"Origin": TRUSTED_ORIGIN},
            json={"email": "trusted@example.com", "password": PASSWORD},
        )
        assert trusted_register.status_code == 201
        assert trusted_register.headers["access-control-allow-origin"] == TRUSTED_ORIGIN
        assert trusted_register.headers["access-control-allow-credentials"] == "true"
