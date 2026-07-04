from fastapi.templating import Jinja2Templates
from markupsafe import Markup, escape
from starlette.requests import Request

from app.security import get_csrf_token

templates = Jinja2Templates(directory="app/templates")


def csrf_input(request: Request) -> Markup:
    token = get_csrf_token(request)
    return Markup(f'<input type="hidden" name="csrf_token" value="{escape(token)}">')


templates.env.globals["csrf_input"] = csrf_input
