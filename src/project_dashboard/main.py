from fastapi import FastAPI

from project_dashboard.api.exception_handlers import register_exception_handlers
from project_dashboard.api.v1.auth import router as auth_router

app = FastAPI()
app.include_router(auth_router)

register_exception_handlers(app)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
