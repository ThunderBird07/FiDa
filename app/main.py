from fastapi import FastAPI
from .api.v1.router import api_router

app = FastAPI(title="FiDa", version="0.1.0")

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(api_router,prefix="/v1")