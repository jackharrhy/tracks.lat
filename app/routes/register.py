from typing import Annotated

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from asyncpg import Connection
from loguru import logger

from app.db import get_connection_from_pool, create_user
from app.fastapi_utils import templates, setup_user_session
from app.settings import settings

router = APIRouter()


@router.get("/lon/register")
async def register_page_route(request: Request):
    if not settings.registrations_open:
        # TODO this should be a redirect + flash message instead
        return "Registrations are closed"

    return templates.TemplateResponse(
        "register.html",
        {
            "request": request,
            "registrations_open": settings.registrations_open,
        },
    )


@router.post("/lon/register")
async def register_route(
    request: Request,
    username: Annotated[str, Form()],
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    con: Connection = Depends(get_connection_from_pool),
):
    if not settings.registrations_open:
        # TODO this should be a flash message instead
        return "Registrations are closed"

    errors = []

    if not username.isalnum():
        errors.append("Username must contain alphanumeric characters only")

    if len(username) < 3 or len(username) > 10:
        errors.append("Username must be between 3 and 10 characters")

    if len(password) < 8 or len(password) > 64:
        errors.append(
            "Password must be at least 8 characters and at most 64 characters"
        )

    if "@" not in email or "." not in email:
        errors.append("Invalid email address")

    if errors:
        # TODO this should be a flash message instead
        return ", ".join(errors)

    role = "user"

    user_id = await create_user(con, username, email, password, role)

    logger.info(f"Registered user {username} with ID {user_id}")

    setup_user_session(request, user_id, username, role)

    return RedirectResponse(f"/lon/{username}", status_code=303)
