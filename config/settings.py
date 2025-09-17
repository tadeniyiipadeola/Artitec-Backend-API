# config/settings.py
import os

DB_URL = os.getenv("DB_URL", "mysql+pymysql://user:pass@127.0.0.1:3306/artitec")
JWT_SECRET = os.getenv("JWT_SECRET", "replace_me")
JWT_ISS = "artitec.api"
ACCESS_TTL_MIN = 15
REFRESH_TTL_DAYS = 30