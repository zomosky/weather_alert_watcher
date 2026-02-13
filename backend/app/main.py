from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.core.database import Base, engine, SessionLocal
from app.services.ingestion import IngestionInput, IngestionService
from app.storage.repository import WeatherRepository

settings = get_settings()

app = FastAPI(title=settings.app_name)
app.include_router(router, prefix=settings.api_prefix)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        repository = WeatherRepository(db)
        service = IngestionService(repository, settings=settings)
        service.refresh(
            IngestionInput(
                lat=settings.default_lat,
                lon=settings.default_lon,
                province=settings.default_province,
                label=settings.default_label,
            )
        )
    finally:
        db.close()
