from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.core.config import get_settings
from app.core.database import Base, engine

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(router, prefix=settings.api_prefix)
app.add_middleware(CORSMiddleware,
                   allow_origins=[s.strip() for s in settings.cors_origins.split(",") if s.strip()],
                   allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
