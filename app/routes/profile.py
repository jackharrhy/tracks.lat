from typing import Annotated

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import StreamingResponse, RedirectResponse
from asyncpg import Connection
import io

import shapely
import geopandas as gpd
import matplotlib.pyplot as plt

from app.db import get_connection_from_pool
from app.fastapi_utils import templates, not_found_resp, activity_to_emoji

router = APIRouter()


@router.get("/lon/{username}")
async def display_user_route(
    request: Request, username: str, con: Connection = Depends(get_connection_from_pool)
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


@router.get("/lon/{username}/{slug}.png")
async def display_track_as_png(
    request: Request,
    username: str,
    slug: str,
    con: Connection = Depends(get_connection_from_pool),
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
    gdf.plot(ax=ax, color="white", linewidth=2)
    fig.axes[0].set_axis_off()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0, transparent=True)
    plt.close(fig)

    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


@router.get("/lon/{username}/{slug}")
async def display_tracks(
    request: Request,
    username: str,
    slug: str,
    con: Connection = Depends(get_connection_from_pool),
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


@router.post("/lon/{username}/{slug}")
async def track_actions(
    request: Request,
    username: str,
    slug: str,
    method: Annotated[str, Form()],
    con: Connection = Depends(get_connection_from_pool),
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
