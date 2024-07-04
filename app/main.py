from contextlib import asynccontextmanager

from starlette.middleware.sessions import SessionMiddleware
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from app.db import create_pool, close_pool
from app.settings import settings
from app.routes import (
    admin_router,
    homepage_router,
    login_router,
    logout_router,
    profile_router,
    register_router,
    upload_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_pool()
    yield
    await close_pool()


app = FastAPI(lifespan=lifespan)

app.add_middleware(SessionMiddleware, secret_key=settings.session_secret_key)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(homepage_router)
app.include_router(login_router)
app.include_router(logout_router)
app.include_router(register_router)
app.include_router(admin_router)
app.include_router(upload_router)

app.include_router(profile_router)


@app.get("/")
async def root():
    return RedirectResponse("/lon/")
