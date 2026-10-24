
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError


from app.api.v1.companies import router as companies_router
from app.core.config import settings
from app.db.session import engine

app = FastAPI(
    title=settings.app_name,
    description="Agentic Sales CRM and Revenue Intelligence API",
    version=settings.app_version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(companies_router, prefix="/api/v1")

@app.get("/")
def home():
    return {
        "name": settings.app_name,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "revpilot-api",
        "version": settings.app_version,
    }


@app.get("/api/v1")
def api_root():
    return {
        "name": settings.app_name,
        "message": "Sales CRM API is running",
    }


@app.get("/health/database")
def database_health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "connected", "database": "postgresql"}
    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed. Check PostgreSQL and backend/.env.",
        )
