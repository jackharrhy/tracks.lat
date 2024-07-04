from fastapi import Request, Depends, APIRouter
from asyncpg import Connection

from app.db import get_connection_from_pool
from app.fastapi_utils import templates, not_found_resp

router = APIRouter()


@router.get("/lon/")
async def display_root_route(
    request: Request,
    con: Connection = Depends(get_connection_from_pool),
    format: str = None,
):
    if format is None or format == "html":
        return templates.TemplateResponse("index.html", {"request": request})

    if format != "json":
        return not_found_resp(request)

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
