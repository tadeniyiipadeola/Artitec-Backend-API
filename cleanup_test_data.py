#!/usr/bin/env python3
"""Cleanup test data from database"""

from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

engine = create_engine(os.getenv('DB_URL'))

with engine.connect() as conn:
    # Delete test users
    conn.execute(text("DELETE FROM users WHERE email = 'john.perry@perryhomes.com'"))
    conn.execute(text("DELETE FROM users WHERE email = 'sarah.sales@perryhomes.com'"))

    # Delete test builder profiles
    conn.execute(text("DELETE FROM builder_profiles WHERE name = 'Perry Homes'"))

    conn.commit()
    print("✓ Cleaned up test data")
