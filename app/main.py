from typing import Annotated
import io

from fastapi import FastAPI, Request, Depends, UploadFile, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
import shapely.wkb
import geopandas as gpd
import matplotlib.pyplot as plt
from asyncpg import Connection

from app.db import get_connection_from_pool, create_pool, close_pool
from app.settings import settings

app = FastAPI()


@app.on_event("startup")
async def startup():
    await create_pool()


@app.on_event("shutdown")
async def shutdown():
    await close_pool()


async def get_con():
    async with get_connection_from_pool() as con:
        yield con


templates = Jinja2Templates(directory="templates")


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
async def display_root(request: Request, con: Connection = Depends(get_con)):
    records = await con.fetch("SELECT id, name, activity FROM tracks")

    tracks = [
        {
            "id": record["id"],
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


@app.post("/lon/")
async def upload_gpx(
    gpx: UploadFile,
    secret_password: Annotated[str, Form()],
    con: Connection = Depends(get_con),
):
    if settings.secret_password != secret_password:
        return RedirectResponse(
            "https://www.youtube.com/watch?v=RfiQYRn7fBg", status_code=303
        )

    row = gpd.read_file(gpx.file, layer="tracks", driver="GPX").iloc[0]
    name = row["name"]
    geometry = row["geometry"].wkt
    activity = row["type"]

    record = await con.fetchrow(
        """
        INSERT INTO tracks (name, geometry, activity)
        VALUES ($1, ST_SetSRID(ST_GeomFromText($2), 4326), $3)
        RETURNING id
        """,
        name,
        geometry,
        activity,
    )

    if record is None:
        raise Exception("Failed to insert track")

    id = record["id"]

    return RedirectResponse(f"/lon/map/{id}", status_code=303)


@app.get("/lon/map/{image_id}.png")
async def display_map_by_id_as_png(
    request: Request, image_id: int, con: Connection = Depends(get_con)
):
    record = await con.fetchrow(
        "SELECT geometry FROM tracks WHERE id = $1",
        image_id,
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
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")


@app.get("/lon/map/{image_id}")
async def display_map_by_id(
    request: Request, image_id: int, con: Connection = Depends(get_con)
):
    record = await con.fetchrow(
        "SELECT id, name, activity FROM tracks WHERE id = $1",
        image_id,
    )

    if record is None:
        return not_found_resp(request)

    return templates.TemplateResponse(
        "map.html",
        {
            "request": request,
            "name": record["name"],
            "track_id": record["id"],
            "activity_emoji": activity_to_emoji(record["activity"]),
        },
    )
