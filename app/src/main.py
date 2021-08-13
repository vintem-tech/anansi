from fastapi import FastAPI
from .services.start import Config

app = FastAPI()


@app.on_event("startup")
async def load_configs():
    Config().create_if_do_not_exist()
