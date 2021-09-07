from .router import web_app, templates, HTMLResponse, Request

@web_app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(
        "home.html", {"request": request}
    )

@web_app.get("/home", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "home.html", {"request": request}
    )
