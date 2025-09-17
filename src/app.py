# src/app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.auth import router as auth_router

# DEV-ONLY: create tables + seed user_types at startup
from config.db import engine, SessionLocal
from model.base import Base
from model.user import UserType

app = FastAPI(title="Artitec API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], allow_credentials=True
)

app.include_router(auth_router, prefix="/v1/auth", tags=["auth"])

@app.on_event("startup")
def _startup():
    # Create tables if they don't exist (dev)
    Base.metadata.create_all(engine)

    # Seed user_types if missing (dev)
    db = SessionLocal()
    try:
        codes = {c for (c,) in db.query(UserType.code).all()}
        needed = [
            ("homeowner", "Homeowner"),
            ("builder", "Builder"),
            ("hoa_admin", "HOA Admin"),
            ("admin", "Platform Admin"),
        ]
        for code, display in needed:
            if code not in codes:
                db.add(UserType(code=code, display_name=display))
        db.commit()
    finally:
        db.close()

# Optional quick health route
@app.get("/health")
def health():
    return {"ok": True}