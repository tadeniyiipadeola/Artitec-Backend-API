# config/settings.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database configuration
DB_URL = os.getenv("DB_URL", "mysql+pymysql://user:pass@127.0.0.1:3306/artitec")

# JWT & Security settings
# Accept either JWT_SECRET or SECRET_KEY, and default to a dev key if nothing provided
JWT_SECRET = os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY") or "dev-secret-artitec-key"
# Allow either JWT_ALG or JWT_ALGORITHM
JWT_ALG = os.getenv("JWT_ALG") or os.getenv("JWT_ALGORITHM") or "HS256"
JWT_ISS = os.getenv("JWT_ISS", "artitec.api")

ACCESS_TTL_MIN = int(os.getenv("ACCESS_TTL_MIN", 15))      # Access token validity (minutes)
REFRESH_TTL_DAYS = int(os.getenv("REFRESH_TTL_DAYS", 30))  # Refresh token validity (days)

# Application environment
APP_ENV = os.getenv("APP_ENV", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# SchoolDigger API configuration
SCHOOLDIGGER_API_KEY = os.getenv("SCHOOLDIGGER_API_KEY", "")
