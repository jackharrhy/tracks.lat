from fastapi import Request, Depends, APIRouter
from asyncpg import Connection

from app.db import get_connection_from_pool
from app.fastapi_utils import templates, not_found_resp, activity_to_emoji

router = APIRouter()


async def html_template(request: Request, con: Connection):
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


async def json_data(con: Connection):
    aggregates = await con.fetchrow(
        """
        SELECT
            ST_AsGeoJSON(ST_Centroid(ST_Extent(geometry)))::json as center,
            ST_AsGeoJSON(ST_Extent(geometry))::json as extent
        FROM
            tracks
    """
    )

    tracks = await con.fetch(
        """
        SELECT
            tracks.id as id,
            slug,
            name,
            activity,
            username,
            ST_AsGeoJSON(geometry)::json as geometry
        FROM
            tracks
        JOIN
            users ON tracks.user_id = users.id
    """
    )

    return {
        "aggregates": aggregates,
        "tracks": tracks,
    }


@router.get("/lon/")
async def display_root_route(
    request: Request,
    con: Connection = Depends(get_connection_from_pool),
    format: str = None,
):
    if format is None or format == "html":
        return await html_template(request, con)

    if format == "json":
        return await json_data(con)

    return not_found_resp(request)
