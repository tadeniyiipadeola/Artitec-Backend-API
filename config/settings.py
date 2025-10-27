# config/settings.py
import os

# Database configuration
DB_URL = os.getenv("DB_URL", "mysql+pymysql://user:pass@127.0.0.1:3306/artitec")

# JWT & Security settings
JWT_SECRET = os.getenv("JWT_SECRET", "replace_me")
JWT_ALG = os.getenv("JWT_ALG", "HS256")
JWT_ISS = os.getenv("JWT_ISS", "artitec.api")

ACCESS_TTL_MIN = int(os.getenv("ACCESS_TTL_MIN", 15))      # Access token validity (minutes)
REFRESH_TTL_DAYS = int(os.getenv("REFRESH_TTL_DAYS", 30))  # Refresh token validity (days)

# Application environment
APP_ENV = os.getenv("APP_ENV", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")