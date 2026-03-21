from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.v1.router import api_router

app = FastAPI(title="FiDa", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "https://127.0.0.1:5500",
        "https://localhost:5500",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://127.0.0.1:8000",
        "http://fida.local",
        "http://fida.local:5500",
        "http://fida.local:8000",
        "https://fida.local",
        "https://fida.local:5500",
        "https://fida.local:8000",
        "http://172.28.46.25",
        "http://172.28.46.25:80",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(api_router,prefix="/v1")