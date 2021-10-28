from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.API.router import api
#from src.utils.databases.sql.core.init_db import init_db
#from src.utils.databases.sql.core.session import SessionLocal
from src.web.routes import router

#init_db(db=SessionLocal())

app = FastAPI()
#app.include_router(api, prefix="/api/v1")
app.mount("", router.web_app)


# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=[
#         "http://localhost",
#         "https://localhost",
#         "http://localhost:8000",
#         "https://localhost:8000",
#         "http://localhost:8000/docs#/",
#         "https://localhost:8000/docs#/",
#     ],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


@app.get("/")
def read_root():
    return {"Hello": "World"}
