
# 🏗️ Artitec Backend Development

The **Artitec Backend** is a scalable API built with **FastAPI**, **SQLAlchemy**, and **Pydantic**, designed to power the **Artitec Platform** — a modern real estate technology ecosystem connecting **Builders**, **Communities**, **Sales Reps**, and **Buyers**.  

It serves as the data and business logic backbone for Artitec’s SwiftUI front-end, providing endpoints for authentication, profiles, listings, communities, social interactions, and analytics.

---

## 🚀 Features

- 🔐 **User Authentication** — Secure registration, login, and JWT-based sessions.  
- 👤 **Role-Based Profiles** — Modular design for Buyers, Builders, Community Admins, and Sales Reps.  
- 🏡 **Property Management** — Full CRUD for listings, media, and project portfolios.  
- 🏘️ **Community Integration** — Manage HOA/Community pages, admins, and events.  
- 💬 **Social Feed** — Create posts, comment, and interact with the builder community.  
- 📊 **Analytics & Insights** — Track property views, saves, and engagement metrics.  
- ☁️ **Media Uploads** — Supports avatars, builder logos, and property images (local or cloud).  

---

## 🧱 Project Structure

```bash
src/
├── app.py                    # FastAPI entrypoint
├── core/
│   ├── config.py             # Settings, environment variables
│   ├── security.py           # JWT, password hashing
│   └── database.py           # SQLAlchemy session + engine
│
├── model/
│   ├── user.py               # Base User model
│   ├── profiles/
│   │   ├── buyer.py
│   │   ├── builder.py
│   │   ├── community_admin.py
│   │   └── sales_rep.py
│   ├── organization.py       # Builder orgs, communities, etc.
│   ├── property.py           # Property listings
│   ├── project.py            # Builder projects / portfolios
│   ├── board.py              # Saved boards / collections
│   └── post.py               # Feed / social posts
│
├── schema/
│   ├── user_schema.py
│   ├── auth_schema.py
│   ├── buyer_schema.py
│   ├── builder_schema.py
│   ├── community_schema.py
│   ├── property_schema.py
│   ├── post_schema.py
│   └── ...                   # etc.
│
├── routes/
│   ├── __init__.py
│   ├── v1/
│   │   ├── auth.py           # /v1/auth/register, /login, /refresh
│   │   ├── users.py          # /v1/users/{id}, profile updates
│   │   ├── buyers.py         # /v1/buyers/
│   │   ├── builders.py       # /v1/builders/
│   │   ├── communities.py    # /v1/communities/
│   │   ├── properties.py     # /v1/properties/
│   │   ├── posts.py          # /v1/posts/
│   │   ├── boards.py         # /v1/boards/
│   │   ├── analytics.py      # /v1/analytics/ (views, saves, etc.)
│   │   └── uploads.py        # /v1/uploads/avatars, media
│
├── service/
│   ├── auth_service.py
│   ├── user_service.py
│   ├── property_service.py
│   ├── builder_service.py
│   ├── community_service.py
│   ├── email_service.py
│   └── ...
│
├── utils/
│   ├── logger.py
│   ├── validators.py
│   ├── exceptions.py
│   └── media.py
│
└── tests/
    ├── test_auth.py
    ├── test_user.py
    ├── test_property.py
    └── ...
```

---

## 🌐 API Overview

All endpoints are versioned under `/v1/` for maintainability and smooth upgrades.

| Module | Base Path | Description |
|--------|------------|-------------|
| **Auth** | `/v1/auth` | Handles user registration, login, and token refresh |
| **Users** | `/v1/users` | Generic user info and profile updates |
| **Buyers** | `/v1/buyers` | Buyer preferences, saved homes, and profiles |
| **Builders** | `/v1/builders` | Builder portfolios, org details, awards, and projects |
| **Communities** | `/v1/communities` | HOA/Community pages, phases, and events |
| **Properties** | `/v1/properties` | Property listing creation, retrieval, and updates |
| **Posts** | `/v1/posts` | Feed posts, comments, and engagement |
| **Boards** | `/v1/boards` | Saved boards or collections of listings/builders |
| **Analytics** | `/v1/analytics` | Tracks property views, saves, and engagement metrics |
| **Uploads** | `/v1/uploads` | Media upload endpoints for images and files |

---

## 🧪 Example API Usage

### 🧍 Register a User
**POST** `/v1/auth/register`
```json
{
  "email": "samuel@artitec.com",
  "password": "securePass123",
  "role": "builder"
}
```

**Response**
```json
{
  "id": 1,
  "email": "samuel@artitec.com",
  "role": "builder",
  "token": "eyJhbGciOiJIUzI1NiIsInR..."
}
```

---

### 🏡 Get Property by ID
**GET** `/v1/properties/42`
```json
{
  "id": 42,
  "title": "Modern Craftsman Home",
  "price": 850000,
  "builder_id": 3,
  "community_id": 7,
  "photos": [
    "https://cdn.artitec.com/property/42/front.jpg"
  ]
}
```

---

## 🧰 Development Setup

### Local Development
```bash
# Clone the repository
git clone https://github.com/artitec-tech/backend.git
cd backend

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn src.app:app --reload
```

### NAS / Docker Deployment
Your **Synology NAS** hosts both the development and production environments.

Typical directory layout:
```
/volume1/artitec-dev
/volume1/artitec-prod
```

Run containers using `docker-compose.yml` with environment variables for:
- `DB_HOST`, `DB_USER`, `DB_PASS`, `DB_NAME`
- `JWT_SECRET`, `ACCESS_TOKEN_EXPIRE_MINUTES`
- Optional integrations (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, etc.)

---

## 🧭 Design Principles

- **Versioned APIs** — Consistent and future-proof (`/v1/`, `/v2/`, ...).  
- **Service Layer Abstraction** — Keeps route logic thin and maintainable.  
- **Modular Roles** — Separate profiles and logic for each user type.  
- **Database Integrity** — Strong foreign key and relationship mapping.  
- **Scalability First** — Organized to expand with additional microservices or modules.

---

## 📬 Contact

**Developed by:** Artitec Technology  
**Lead Developer:** Samuel Adeniyi  
**Website:** [https://woodbridgebungalow.lodgify.com](https://woodbridgebungalow.lodgify.com)  
**Email:** adeniyifamilia@gmail.com  

---