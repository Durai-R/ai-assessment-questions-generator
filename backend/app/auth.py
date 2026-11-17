import secrets
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from jwt.exceptions import InvalidTokenError
from pymongo.errors import DuplicateKeyError

from app.config import Settings
from app.schemas import Credentials, UserResponse


router = APIRouter(prefix="/api/auth", tags=["authentication"])
password_hasher = PasswordHasher()
dummy_password_hash = password_hasher.hash(secrets.token_urlsafe(32))


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def user_response(document: dict) -> UserResponse:
    return UserResponse(id=str(document["_id"]), email=document["email"])


def unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required.",
    )


def create_access_token(user_id: ObjectId, settings: Settings) -> str:
    now = utc_now()
    return jwt.encode(
        {
            "sub": str(user_id),
            "iat": now,
            "exp": now + timedelta(minutes=settings.jwt_expiry_minutes),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def auth_cookie_options(settings: Settings) -> dict:
    return {
        "key": settings.auth_cookie_name,
        "path": "/",
        "domain": settings.auth_cookie_domain,
        "secure": settings.secure_auth_cookie,
        "httponly": True,
        "samesite": "lax",
    }


async def get_current_user(request: Request) -> dict:
    settings: Settings = request.app.state.settings
    token = request.cookies.get(settings.auth_cookie_name)
    if not token:
        raise unauthorized()

    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp"]},
        )
        subject = claims.get("sub")
        expiration = claims.get("exp")
        if not isinstance(subject, str) or not subject:
            raise unauthorized()
        if isinstance(expiration, bool) or not isinstance(expiration, (int, float)):
            raise unauthorized()
        user_id = ObjectId(subject)
    except (InvalidTokenError, InvalidId, TypeError, KeyError) as exc:
        raise unauthorized() from exc

    user = await request.app.state.database.users.find_one({"_id": user_id})
    if user is None:
        raise unauthorized()
    return user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(credentials: Credentials, request: Request) -> UserResponse:
    document = {
        "email": str(credentials.email),
        "password_hash": password_hasher.hash(credentials.password),
        "created_at": utc_now(),
    }
    try:
        result = await request.app.state.database.users.insert_one(document)
    except DuplicateKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from exc
    return user_response({"_id": result.inserted_id, "email": document["email"]})


@router.post("/login", response_model=UserResponse)
async def login(credentials: Credentials, request: Request, response: Response) -> UserResponse:
    user = await request.app.state.database.users.find_one({"email": str(credentials.email)})
    password_hash = user["password_hash"] if user else dummy_password_hash
    valid_password = True
    try:
        password_hasher.verify(password_hash, credentials.password)
    except VerificationError:
        valid_password = False

    if user is None or not valid_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    token = create_access_token(user["_id"], request.app.state.settings)
    settings: Settings = request.app.state.settings
    response.set_cookie(
        **auth_cookie_options(settings),
        value=token,
        max_age=settings.jwt_expiry_minutes * 60,
    )
    return user_response(user)


@router.get("/me", response_model=UserResponse)
async def me(user: dict = Depends(get_current_user)) -> UserResponse:
    return user_response(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, response: Response) -> Response:
    response.delete_cookie(**auth_cookie_options(request.app.state.settings))
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
