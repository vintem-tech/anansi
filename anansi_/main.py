from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    return {"Wellcome": "Hi, I'm Anansi, a trading bot and market analysis toolbox. "}