
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from fastapi import Depends
from app.api.dependencies import get_current_user
from app.api.v1.ai_policy import router as ai_policy_router
from app.api.v1.policies import router as policies_router
from app.api.v1.intelligence import router as intelligence_router
from app.api.v1.deals import router as deals_router
from app.api.v1.activities import router as activities_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.deals import router as deals_router
from app.api.v1.leads import router as leads_router
from app.api.v1.companies import router as companies_router
from app.api.v1.contacts import router as contacts_router
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
from fastapi import Depends
from app.api.dependencies import get_current_user
from app.api.v1.auth import router as auth_router

# app.include_router(companies_router, prefix="/api/v1")
app.include_router(contacts_router, prefix="/api/v1")
app.include_router(leads_router, prefix="/api/v1")
app.include_router(deals_router, prefix="/api/v1")
app.include_router(activities_router, prefix="/api/v1")
app.include_router(tasks_router, prefix="/api/v1")
app.include_router(deals_router, prefix="/api/v1")
app.include_router(intelligence_router, prefix="/api/v1")
app.include_router(policies_router, prefix="/api/v1")
app.include_router(ai_policy_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")


# Authentication routes remain public so users can log in.
app.include_router(
    auth_router,
    prefix="/api/v1",
)

# CRM routes require a valid bearer token.
app.include_router(
    companies_router,
    prefix="/api/v1",
    dependencies=[Depends(get_current_user)],
)

app.include_router(
    contacts_router,
    prefix="/api/v1",
    dependencies=[Depends(get_current_user)],
)

app.include_router(
    leads_router,
    prefix="/api/v1",
    dependencies=[Depends(get_current_user)],
)

app.include_router(
    deals_router,
    prefix="/api/v1",
    dependencies=[Depends(get_current_user)],
)

app.include_router(
    activities_router,
    prefix="/api/v1",
    dependencies=[Depends(get_current_user)],
)

app.include_router(
    tasks_router,
    prefix="/api/v1",
    dependencies=[Depends(get_current_user)],
)

app.include_router(
    intelligence_router,
    prefix="/api/v1",
    dependencies=[Depends(get_current_user)],
)

app.include_router(
    policies_router,
    prefix="/api/v1",
    dependencies=[Depends(get_current_user)],
)

app.include_router(
    ai_policy_router,
    prefix="/api/v1",
    dependencies=[Depends(get_current_user)],
)


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
