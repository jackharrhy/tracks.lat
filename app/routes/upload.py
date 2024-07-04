from fastapi import Request, Depends, UploadFile, APIRouter
from fastapi.responses import RedirectResponse
import geopandas as gpd
from asyncpg import Connection
from loguru import logger

from app.db import get_connection_from_pool
from app.fastapi_utils import templates

router = APIRouter()


@router.get("/lon/upload")
async def upload_gpx_page_route(request: Request):
    # TODO make generic, flash message
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


@router.post("/lon/upload")
async def upload_gpx_route(
    request: Request,
    gpx: UploadFile,
    con: Connection = Depends(get_connection_from_pool),
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

    if name.lower().endswith(".gpx"):
        name = name[:-4]

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
