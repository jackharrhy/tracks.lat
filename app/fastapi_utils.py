from typing import Dict, Any

from fastapi import Request
from fastapi.templating import Jinja2Templates


def user_context(request: Request) -> Dict[str, Any]:
    return {
        "user": request.session.get("user"),
    }


templates = Jinja2Templates(directory="templates", context_processors=[user_context])


def activity_to_emoji(activity: str):
    match activity:
        case "walking":
            return "🚶"
        case _:
            return "❓"


def setup_user_session(request: Request, id: int, username: str, role: str):
    request.session["user"] = {
        "id": id,
        "username": username,
        "role": role,
    }


# TODO make this the page when a route throws a 404
def not_found_resp(request: Request):
    return templates.TemplateResponse(
        "404.html",
        {
            "request": request,
        },
    )
