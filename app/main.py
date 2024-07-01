from typing import Annotated
import io
from contextlib import asynccontextmanager

import typing
import bcrypt
from starlette.middleware.sessions import SessionMiddleware
from fastapi import FastAPI, Request, Depends, UploadFile, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
import shapely.wkb
import geopandas as gpd
import matplotlib.pyplot as plt
from asyncpg import Connection
from loguru import logger

from app.db import get_connection_from_pool, create_pool, close_pool
from app.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_pool()
    yield
    await close_pool()


app = FastAPI(lifespan=lifespan)

app.add_middleware(SessionMiddleware, secret_key=settings.session_secret_key)


async def get_con():
    async with get_connection_from_pool() as con:
        yield con


def user_context(request: Request) -> typing.Dict[str, typing.Any]:
    return {
        "user": request.session.get("user"),
    }


templates = Jinja2Templates(directory="templates", context_processors=[user_context])


def not_found_resp(request: Request):
    return templates.TemplateResponse(
        "404.html",
        {
            "request": request,
        },
    )


@app.get("/")
async def root():
    return RedirectResponse("/lon/")


def activity_to_emoji(activity: str):
    match activity:
        case "walking":
            return "🚶"
        case _:
            return "❓"


@app.get("/lon/", response_class=HTMLResponse)
async def display_root_route(request: Request, con: Connection = Depends(get_con)):
    records = await con.fetch(
        """
        SELECT
            tracks.id as id, slug, name, activity, username
        FROM
            tracks
        JOIN
            users ON tracks.user_id = users.id
    """
    )

    tracks = [
        {
            "username": record["username"],
            "slug": record["slug"],
            "name": record["name"],
            "activity_emoji": activity_to_emoji(record["activity"]),
        }
        for record in records
    ]

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "tracks": tracks,
        },
    )


@app.get("/lon/upload")
async def upload_gpx_page_route(request: Request):
    if request.session.get("user") is None:
        return RedirectResponse("/lon/login", status_code=303)

    return templates.TemplateResponse(
        "upload.html",
        {
            "request": request,
        },
    )


def slugify_name(name: str):
    name = name.encode("ascii", "ignore").decode("utf-8")
    name = name.lower()
    name = " ".join(name.split())
    name = name.replace(" ", "-")
    return name


@app.post("/lon/upload")
async def upload_gpx_route(
    request: Request,
    gpx: UploadFile,
    con: Connection = Depends(get_con),
):
    user = request.session.get("user")

    if user is None:
        return RedirectResponse("/lon/login", status_code=303)

    number_of_tracks_for_user = await con.fetchval(
        "SELECT COUNT(*) FROM tracks WHERE user_id = $1",
        user["id"],
    )

    if number_of_tracks_for_user is None or number_of_tracks_for_user >= 50:
        # TODO this should be a flash message instead
        return "You have reached the maximum number of tracks, poke Jack"

    row = gpd.read_file(gpx.file, layer="tracks", driver="GPX").iloc[0]
    name = row["name"] or gpx.filename
    geometry = row["geometry"].wkt
    activity = row["type"] or "walking"
    user_id = user["id"]
    slug = slugify_name(name)

    errors = []

    if len(name) < 3 or len(name) > 100:
        errors.append("Name must be between 3 and 100 characters")

    if len(activity) > 20:
        errors.append("Activity must be at most 20 characters")

    if len(errors) > 0:
        # TODO this should be a flash message instead
        return ", ".join(errors)

    record_id = await con.fetchval(
        """
        INSERT INTO tracks (name, slug, geometry, activity, user_id)
        VALUES ($1, $2, ST_SetSRID(ST_GeomFromText($3), 4326), $4, $5)
        RETURNING id
        """,
        name,
        slug,
        geometry,
        activity,
        user_id,
    )

    if record_id is None:
        raise Exception("Failed to insert track")

    logger.info(f"Inserted track {name} with ID {record_id}")

    return RedirectResponse(f"/lon/{user['username']}/{slug}", status_code=303)


@app.get("/lon/login")
async def login_page_route(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
        },
    )


def setup_user_session(request: Request, id: int, username: str, role: str):
    request.session["user"] = {
        "id": id,
        "username": username,
        "role": role,
    }


@app.post("/lon/login")
async def login_route(
    request: Request,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    con: Connection = Depends(get_con),
):
    user = await con.fetchrow(
        "SELECT id, username, password_hash, role FROM users WHERE username = $1",
        username,
    )

    if user is None or not bcrypt.checkpw(
        password.encode("utf-8"), user["password_hash"]
    ):
        # TODO this should be a flash message instead
        return "Invalid username or password"

    setup_user_session(request, user["id"], user["username"], user["role"])

    return RedirectResponse(f"/lon/{user['username']}", status_code=303)


@app.post("/lon/logout")
async def logout_route(request: Request):
    request.session.clear()
    return RedirectResponse("/lon/", status_code=303)


@app.get("/lon/register")
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


@app.get("/lon/admin")
async def admin_page_route(request: Request):
    user = request.session.get("user")

    if user is None:
        return RedirectResponse("/lon/login", status_code=303)

    if user["role"] != "admin":
        return "nuh uh 🚫"

    return templates.TemplateResponse("admin.html", {"request": request})

@app.post("/lon/admin")
async def admin_route(request: Request, action: Annotated[str, Form()], con: Connection = Depends(get_con)):
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

async def create_user(
    con: Connection, username: str, email: str, password: str, role: str
):
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    user_id = await con.fetchval(
        """
        INSERT INTO users (username, email, password_hash, role)
        VALUES ($1, $2, $3, $4)
        RETURNING id
        """,
        username,
        email,
        hashed_password,
        role,
    )

    if user_id is None:
        raise Exception("Failed to insert user")

    return user_id


@app.post("/lon/register")
async def register_route(
    request: Request,
    username: Annotated[str, Form()],
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    con: Connection = Depends(get_con),
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


@app.get("/lon/{username}")
async def display_user_route(
    request: Request, username: str, con: Connection = Depends(get_con)
):
    user = await con.fetchrow(
        "SELECT id, username FROM users WHERE username = $1",
        username,
    )

    if user is None:
        return not_found_resp(request)

    records = await con.fetch(
        "SELECT slug, name, activity FROM tracks WHERE user_id = $1", user["id"]
    )

    tracks = [
        {
            "slug": record["slug"],
            "name": record["name"],
            "activity_emoji": activity_to_emoji(record["activity"]),
            "username": username,
        }
        for record in records
    ]

    return templates.TemplateResponse(
        "user.html",
        {
            "request": request,
            "username": user["username"],
            "tracks": tracks,
        },
    )


@app.get("/lon/{username}/{slug}.png")
async def display_track_as_png(
    request: Request, username: str, slug: str, con: Connection = Depends(get_con)
):
    record = await con.fetchrow(
        """
        SELECT
            geometry
        FROM tracks
        JOIN users ON tracks.user_id = users.id
        WHERE users.username = $1 AND tracks.slug = $2
        """,
        username,
        slug,
    )

    if record is None:
        return not_found_resp(request)

    wkb_str = record.get("geometry")
    wkb = shapely.wkb.loads(wkb_str)

    gdf = gpd.GeoDataFrame({"geometry": [wkb]})
    fig = plt.figure()
    ax = fig.add_subplot(111)
    gdf.plot(ax=ax)
    fig.axes[0].set_axis_off()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0)
    plt.close(fig)

    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


@app.get("/lon/{username}/{slug}")
async def display_tracks(
    request: Request, username: str, slug: str, con: Connection = Depends(get_con)
):
    record = await con.fetchrow(
        """
        SELECT
            slug, name, activity, username
        FROM tracks
        JOIN users ON tracks.user_id = users.id
        WHERE users.username = $1 AND tracks.slug = $2
        """,
        username,
        slug,
    )

    if record is None:
        return not_found_resp(request)

    return templates.TemplateResponse(
        "track.html",
        {
            "request": request,
            "slug": record["slug"],
            "name": record["name"],
            "activity_emoji": activity_to_emoji(record["activity"]),
            "username": record["username"],
        },
    )


@app.post("/lon/{username}/{slug}")
async def track_actions(
    request: Request,
    username: str,
    slug: str,
    method: Annotated[str, Form()],
    con: Connection = Depends(get_con),
):
    user = request.session.get("user")

    if user is None or user["username"] != username:
        return RedirectResponse("/lon/login", status_code=303)

    match method:
        case "DELETE":
            await con.execute(
                """
                DELETE FROM tracks
                WHERE slug = $1 AND user_id = $2
                """,
                slug,
                user["id"],
            )

            # TODO this should contain a flash message

            return RedirectResponse(f"/lon/{username}", status_code=303)
        case _:
            return not_found_resp(request)
