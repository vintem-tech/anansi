from fastapi import FastAPI

# from .services.start import Config

dash_server = FastAPI()

# @api.on_event("startup")
# async def load_configs():
#    Config().create_if_do_not_exist()


@dash_server.get("/")
def read_root():
    return {"Hello": "World"}


@dash_server.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}
