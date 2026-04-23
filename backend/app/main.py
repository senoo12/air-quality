from fastapi import FastAPI
from app.api.v1.endpoints import router as api_router
from fastapi.middleware.cors import CORSMiddleware
from app.infrastructure.database import engine
from app.domain import models

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Personalized Sensor API")

origins = [
    "http://localhost:4321",
    "http://127.0.0.1:4321",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include semua route dari v1
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def root():
    return {"message": "Sistem Monitoring Sensor Berjalan"}