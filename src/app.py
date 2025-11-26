# src/app.py
import logging
import os
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from routes.auth import router as auth_router
from routes.user import router as user_router
from routes.password_reset import router as password_reset_router
from routes.email_verification import router as email_verification_router
from routes.profiles import buyers, builder, community, sales_rep, community_admin
from routes.property import property
from routes.admin_helpers import router as admin_router
from routes.admin import router as admin_enterprise_router
from routes.media import router as media_router
from fastapi.openapi.utils import get_openapi

# Optional routers (import if present)
try:
    from routes.social.routes import router as social_router
except Exception:  # pragma: no cover
    social_router = None  # type: ignore



from config.db import engine, SessionLocal
from model.base import Base
from model.user import Role

from model import load_all_models
load_all_models()

logger = logging.getLogger(__name__)


app = FastAPI(title="Artitec API", version="1.0.0")

# Mount uploads directory for serving static files (avatars, images, etc.)
uploads_dir = Path(__file__).parent.parent / "uploads"
uploads_dir.mkdir(exist_ok=True)  # Ensure directory exists
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Artitec API",
        version="1.0.0",
        routes=app.routes,
    )
    # Ensure components/securitySchemes exists
    openapi_schema.setdefault("components", {}).setdefault("securitySchemes", {})["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    # Apply globally so all operations require Bearer unless overridden
    openapi_schema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema
app.openapi = custom_openapi

logging.basicConfig(level=logging.INFO)
logger.info("Artitec API starting…")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
      ],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(auth_router, prefix="/v1/auth", tags=["Authentication"])
app.include_router(password_reset_router, prefix="/v1/auth", tags=["Authentication"])
app.include_router(email_verification_router, prefix="/v1/auth", tags=["Authentication"])
app.include_router(user_router, tags=["Users"])
app.include_router(buyers.router, prefix="/v1/profiles/buyers", tags=["Buyers Profiles"])
app.include_router(builder.router , prefix="/v1/profiles/builders", tags=["Builder Profiles"])
app.include_router(community.router, prefix="/v1/profiles/communities", tags=["Communities Profiles"])
app.include_router(community_admin.router, prefix="/v1/profiles/community-admins", tags=["Community Admin Profiles"])
app.include_router(property.router, prefix="/v1/properties", tags=["Properties Profiles"])
app.include_router(sales_rep.router, prefix="/v1/profiles/sales-reps", tags=["Sales Representative Profiles"])
app.include_router(admin_router, prefix="/admin", tags=["Admin Helpers"])
app.include_router(admin_enterprise_router, prefix="/v1/admin", tags=["Enterprise"])
app.include_router(media_router)  # Now includes /v1/media prefix and all sub-routers



# --- Optional routers (only included if module is available) ---
if social_router is not None:
    app.include_router(social_router)  # already has /v1/social prefix inside


# Minimal roles listing to drive SwiftUI role picker
@app.get("/v1/roles", tags=["Roles"])
def list_roles():
    db = SessionLocal()
    try:
        rows = db.query(Role.key, Role.name).all()
        return [{"key": k, "name": n} for (k, n) in rows]
    finally:
        db.close()



# --- Exception handlers and security headers ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning("Validation error on %s %s: %s", request.method, request.url.path, exc.errors())
    return JSONResponse(status_code=422, content={
        "code": "validation_error",
        "message": "Invalid request",
        "errors": exc.errors(),
    })

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # 4xx/5xx raised intentionally in code
    level = logging.WARNING if 400 <= exc.status_code < 500 else logging.ERROR
    logger.log(level, "HTTPException %s on %s %s: %s", exc.status_code, request.method, request.url.path, exc.detail)
    return JSONResponse(status_code=exc.status_code, content={
        "code": "http_error",
        "message": exc.detail,
    })

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response

def _start_job_monitor():
    """Start background thread to monitor and cleanup stuck jobs"""
    import threading
    import time
    from datetime import datetime, timedelta

    def monitor_stuck_jobs():
        """Periodically check for and reset stuck jobs"""
        while True:
            try:
                time.sleep(300)  # Check every 5 minutes

                from model.collection import CollectionJob
                db = SessionLocal()

                try:
                    # Find jobs stuck for more than 30 minutes
                    cutoff = datetime.utcnow() - timedelta(minutes=30)
                    stuck_jobs = db.query(CollectionJob).filter(
                        CollectionJob.status == "running",
                        CollectionJob.started_at < cutoff
                    ).all()

                    if stuck_jobs:
                        logger.warning(f"🔧 Found {len(stuck_jobs)} stuck job(s), marking as failed")
                        for job in stuck_jobs:
                            job.status = "failed"
                            job.error_message = "Job timed out after 30+ minutes (auto-cleanup)"
                            job.completed_at = datetime.utcnow()
                        db.commit()
                        logger.info(f"✅ Reset {len(stuck_jobs)} stuck job(s)")
                except Exception as e:
                    logger.error(f"❌ Job monitor error: {e}")
                    db.rollback()
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"❌ Job monitor thread crashed: {e}", exc_info=True)

    # Start monitor in daemon thread
    monitor_thread = threading.Thread(target=monitor_stuck_jobs, daemon=True)
    monitor_thread.start()
    logger.info("🔍 Started background job monitor (checks every 5 minutes)")


# NOTE: FastAPI recommends lifespan context for newer apps; startup event is fine for dev.
@app.on_event("startup")
def _startup():
    # Optionally ensure schema in dev if explicitly enabled (prefer Alembic normally)
    if os.getenv("ARTITEC_DEV_CREATE_SCHEMA") == "1":
        Base.metadata.create_all(engine)
        logger.info("DB metadata ensured via SQLAlchemy (dev mode).")
    else:
        logger.info("Skipping Base.metadata.create_all(); use Alembic migrations for schema.")

    # Optionally seed roles (only if tables are present)
    if os.getenv("ARTITEC_SEED_ROLES", "1") == "1":
        db = SessionLocal()
        try:
            keys = {k for (k,) in db.query(Role.key).all()}
            needed = [
                ("buyer", "Buyer"),
                ("builder", "Builder"),
                ("community", "Community"),
                ("community_admin", "Community Admin"),
                ("salesrep", "Sales Representative"),
                ("admin", "Administrator"),
            ]
            for key, name in needed:
                if key not in keys:
                    db.add(Role(key=key, name=name))
            db.commit()
            logger.info("Roles seeded (if missing): %s", sorted({k for (k,) in db.query(Role.key).all()}))
        except Exception as e:
            logger.warning("Skipping role seeding; likely tables not present yet: %s", e)
        finally:
            db.close()

    # Start background job monitor to cleanup stuck jobs
    _start_job_monitor()

# Optional quick health route
@app.get("/health")
def health():
    return {"ok": True}