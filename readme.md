# 🏗️ Artitec Backend

> **Modern Real Estate Platform API**

The **Artitec Backend** is a production-ready RESTful API built with **FastAPI**, **SQLAlchemy**, and **Pydantic** — powering a comprehensive real estate technology ecosystem connecting **Builders**, **Communities**, **Sales Reps**, and **Buyers**.

**Version:** 2.0
**Status:** ✅ Production Ready
**Last Updated:** November 2024

---

## 📚 Documentation

- **[COMPREHENSIVE_DOCUMENTATION.md](COMPREHENSIVE_DOCUMENTATION.md)** - Complete technical documentation
- **[TODO.md](TODO.md)** - Current tasks and roadmap
- **[docs/SWIFTUI_IMPLEMENTATION_GUIDE.md](docs/SWIFTUI_IMPLEMENTATION_GUIDE.md)** - iOS/SwiftUI integration guide

---

## ⚡ Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database credentials

# Run migrations
alembic upgrade head

# Start server
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

---

## 🎯 Key Features

- 🔐 **JWT Authentication** - Secure token-based auth
- 👤 **Role-Based Profiles** - Buyers, Builders, Community Admins, Sales Reps
- 🏡 **Property Management** - Full CRUD for listings
- 🏘️ **Community Platform** - HOA pages, events, amenities
- 💬 **Social Features** - Follows, likes, comments, DMs
- 📊 **Analytics** - Track views, saves, engagement
- 🆔 **Typed IDs** - Self-documenting identifiers (USR-xxx, BYR-xxx, etc.)  

---

## 🏗️ Architecture

```
Artitec Backend/
├── alembic/              # Database migrations
├── config/               # Database & security config
├── model/                # SQLAlchemy models
│   └── profiles/         # Buyer, Builder, Community, etc.
├── schema/               # Pydantic validation schemas
├── routes/               # FastAPI route handlers
│   ├── auth.py
│   ├── user.py
│   └── profiles/         # Profile-specific routes
├── src/                  # Utilities & helpers
└── docs/                 # Documentation
```

---

## 🌐 API Endpoints

All endpoints are versioned under `/v1/` for maintainability.

**Core Modules:**
- `/v1/auth` - Authentication (register, login, role selection)
- `/v1/users` - User management
- `/v1/buyers` - Buyer profiles
- `/v1/profiles/builders` - Builder profiles
- `/v1/communities` - Community management
- `/v1/properties` - Property listings
- `/v1/social` - Follows, likes, comments
- `/v1/dm` - Direct messaging

> **See [COMPREHENSIVE_DOCUMENTATION.md](COMPREHENSIVE_DOCUMENTATION.md) for complete API reference**

---

## 🛠️ Technology Stack

- **Framework:** FastAPI 0.104+
- **ORM:** SQLAlchemy 2.0
- **Validation:** Pydantic v2
- **Database:** MySQL/MariaDB 8.0+
- **Migration:** Alembic
- **Auth:** JWT (python-jose)
- **Deployment:** Docker, Synology NAS

---

## 📬 Contact

**Developer:** Samuel Adeniyi
**Email:** adeniyifamilia@gmail.com
**Website:** [woodbridgebungalow.lodgify.com](https://woodbridgebungalow.lodgify.com)

---

**© 2024 Artitec Technology. All rights reserved.**