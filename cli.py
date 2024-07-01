import asyncio
import typer

app = typer.Typer()


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
