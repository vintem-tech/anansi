from fastapi import FastAPI

from src.API.router import api
from src.web.routes import router
from src.services import start

app = FastAPI()
app.include_router(api, prefix="/api/v1")
app.mount("", router.web_app)

start.populate_database()
