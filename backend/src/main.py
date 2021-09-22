from fastapi import FastAPI

from .API.router import api
from .utils.databases.sql.models import Base, engine
from .web.routes import router

Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(api, prefix="/api/v1")
app.mount("", router.web_app)

# @api.on_event("startup")
# async def load_configs():
#    Config().create_if_do_not_exist()


@app.get("/")
def read_root():
    return {"Hello": "World"}
