from fastapi import FastAPI

from project_dashboard.api.exception_handlers import register_exception_handlers

app = FastAPI()

register_exception_handlers(app)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
