# src/app.py
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from routes.auth import router as auth_router
from routes.user import router as user_router
from routes.profiles import buyers, builder, community
from routes.property import property

# Optional routers (import if present)
try:
    from routes.social.routes import router as social_router
except Exception:  # pragma: no cover
    social_router = None  # type: ignore



from config.db import engine, SessionLocal
from model.base import Base
from model.user import Role

logger = logging.getLogger(__name__)


app = FastAPI(title="Artitec API", version="1.0.0")
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
app.include_router(user_router, tags=["Users"])
app.include_router(buyers.router, prefix="/v1/profiles/buyers", tags=["Buyers Profiles"])
app.include_router(builder.router , prefix="/v1/profiles/builders", tags=["Builder Profiles"])
app.include_router(community.router, prefix="/v1/profiles/communities", tags=["Communities Profiles"])
app.include_router(property.router, prefix="/v1/properties", tags=["Properties Profiles"])


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

# NOTE: FastAPI recommends lifespan context for newer apps; startup event is fine for dev.
@app.on_event("startup")
def _startup():
    # Create tables if they don't exist (dev)
    Base.metadata.create_all(engine)
    logger.info("DB metadata ensured. Seeding roles if missing…")

    # Seed roles if missing (dev)
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
        logger.info("Roles seeded: now present => %s", sorted({k for (k,) in db.query(Role.key).all()}))
    finally:
        db.close()

# Optional quick health route
@app.get("/health")
def health():
    return {"ok": True}