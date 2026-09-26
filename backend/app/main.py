from fastapi import FastAPI

from app.api.routes.queries import router as queries_router
from app.core.config import settings


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Source-backed AI data intelligence for Orbis Labs.",
)
app.include_router(queries_router)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "orbis-labs-api"}
