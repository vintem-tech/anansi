from fastapi import FastAPI

from src.API.router import api
from src.web.routes import router

app = FastAPI()
app.include_router(api, prefix="/api/v1")
app.mount("", router.web_app)


@app.get("/")
def read_root():
    return {"Hello": "World"}
