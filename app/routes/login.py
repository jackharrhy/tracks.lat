from typing import Annotated
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from asyncpg import Connection

from app.fastapi_utils import templates, setup_user_session
from app.db import get_connection_from_pool, check_password

router = APIRouter()


@router.get("/lon/login")
async def login_page_route(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
        },
    )


@router.post("/lon/login")
async def login_route(
    request: Request,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    con: Connection = Depends(get_connection_from_pool),
):
    user = await con.fetchrow(
        "SELECT id, username, password_hash, role FROM users WHERE username = $1",
        username,
    )

    if user is None or not check_password(password, user["password_hash"]):
        # TODO this should be a flash message instead
        return "Invalid username or password"

    setup_user_session(request, user["id"], user["username"], user["role"])

    return RedirectResponse(f"/lon/{user['username']}", status_code=303)
