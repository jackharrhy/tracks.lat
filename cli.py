import asyncio
import typer

app = typer.Typer()


@app.command()
def download_javascript_libs():
    import zipfile
    import tempfile
    from pathlib import Path

    import httpx

    static_dir = Path("static").absolute()

    with tempfile.TemporaryDirectory() as tempdir:
        tempdir = Path(tempdir)
        zip_path = tempdir / "leaflet.zip"
        zip = "https://leafletjs-cdn.s3.amazonaws.com/content/leaflet/v1.9.4/leaflet.zip"

        req = httpx.get(zip)
        with open(zip_path, "wb") as f:
            f.write(req.content)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(tempdir)

        (tempdir / "leaflet.css").rename(static_dir / "leaflet.css")
        (tempdir / "leaflet-src.esm.js").rename(static_dir / "leaflet-src.esm.js")
        (tempdir / "leaflet-src.esm.js.map").rename(static_dir / "leaflet-src.esm.js.map")

        turf = "https://cdn.jsdelivr.net/npm/@turf/turf@7/turf.min.js"

        req = httpx.get(turf)
        with open(static_dir / "turf.min.js", "wb") as f:
            f.write(req.content)

@app.command()
def setup_database():
    from app.db import get_connection, create_db_schema

    async def run():
        connection = await get_connection()
        await create_db_schema(connection)
        await connection.close()

    asyncio.run(run())


@app.command()
def run_dev_api(host: str = "127.0.0.1"):
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=host,
        port=8000,
        reload=True,
        reload_dirs=["app", "templates"],
    )


@app.command()
def display_settings():
    from app.settings import settings

    typer.echo(settings.model_dump_json(indent=2))


@app.command()
def create_user(username: str, email: str, password: str, role: str):
    from app.db import get_connection
    from app.main import create_user

    async def run():
        connection = await get_connection()
        await create_user(connection, username, email, password, role)
        await connection.close()

    asyncio.run(run())


if __name__ == "__main__":
    app()
