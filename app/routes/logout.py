from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

router = APIRouter()


@router.post("/lon/logout")
async def logout_route(request: Request):
    request.session.clear()
    return RedirectResponse("/lon/", status_code=303)
