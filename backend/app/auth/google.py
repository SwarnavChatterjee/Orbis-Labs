"""Google OpenID Connect login using the server-side authorization-code flow."""

from __future__ import annotations

from urllib.parse import urljoin
from uuid import UUID

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionFactory
from app.models.db import User
from app.models.schemas import ApiSuccess


router = APIRouter(prefix="/api/auth", tags=["authentication"])
oauth = OAuth()


def _google_client():
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google authentication is not configured",
        )
    if "google" not in oauth._clients:
        oauth.register(
            name="google",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )
    return oauth.google


@router.get("/google/login")
async def google_login(request: Request) -> RedirectResponse:
    client = _google_client()
    redirect_uri = settings.google_redirect_uri or urljoin(str(request.base_url), "/api/auth/google/callback")
    return await client.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request) -> RedirectResponse:
    client = _google_client()
    try:
        token = await client.authorize_access_token(request)
        userinfo = token.get("userinfo") or await client.userinfo(token=token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Google authentication failed") from exc

    subject = str(userinfo.get("sub", ""))
    email = str(userinfo.get("email", "")).strip().lower()
    if not subject or not email or userinfo.get("email_verified") is not True:
        raise HTTPException(status_code=401, detail="Google account email could not be verified")

    async with SessionFactory() as session:
        user = await session.scalar(select(User).where(User.google_subject == subject))
        if user is None:
            user = await session.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(email=email, google_subject=subject, display_name=userinfo.get("name"))
            session.add(user)
        else:
            user.google_subject = subject
            user.display_name = userinfo.get("name") or user.display_name
        await session.commit()
        await session.refresh(user)

    request.session["user_id"] = str(user.id)
    return RedirectResponse(f"{settings.frontend_url}/app", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/me")
async def current_user(request: Request) -> ApiSuccess:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        user_uuid = UUID(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid authentication session") from exc
    async with SessionFactory() as session:
        user = await session.get(User, user_uuid)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return ApiSuccess(data={"id": str(user.id), "email": user.email, "display_name": user.display_name})


@router.post("/logout")
async def logout(request: Request) -> dict[str, bool]:
    request.session.clear()
    return {"success": True}
