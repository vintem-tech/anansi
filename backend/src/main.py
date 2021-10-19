from fastapi import FastAPI

from src.API.router import api
from src.utils.databases.sql.core.init_db import init_db
from src.web.routes import router
from src.utils.databases.sql.core.session import SessionLocal

init_db(db=SessionLocal())

app = FastAPI()
app.include_router(api, prefix="/api/v1")
app.mount("", router.web_app)

@app.get("/")
def read_root():
    return {"Hello": "World"}
