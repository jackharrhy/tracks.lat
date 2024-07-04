from typing import Annotated
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from asyncpg import Connection
from loguru import logger

from app.db import get_connection_from_pool, create_user
from app.fastapi_utils import templates, not_found_resp

router = APIRouter()


@router.get("/lon/admin")
async def admin_page_route(request: Request):
    user = request.session.get("user")

    if user is None:
        return RedirectResponse("/lon/login", status_code=303)

    if user["role"] != "admin":
        return "nuh uh 🚫"

    return templates.TemplateResponse("admin.html", {"request": request})


@router.post("/lon/admin")
async def admin_route(
    request: Request,
    action: Annotated[str, Form()],
    con: Connection = Depends(get_connection_from_pool),
):
    user = request.session.get("user")

    if user is None:
        return RedirectResponse("/lon/login", status_code=303)

    if user["role"] != "admin":
        return "nuh uh 🚫"

    match action:
        case "create-user":
            form = await request.form()
            username = form.get("username")
            email = form.get("email")
            password = form.get("password")
            role = form.get("role")

            user_id = await create_user(con, username, email, password, role)

            logger.info(f"Created user {username} with ID {user_id}")

            return RedirectResponse("/lon/admin", status_code=303)

    return not_found_resp(request)
