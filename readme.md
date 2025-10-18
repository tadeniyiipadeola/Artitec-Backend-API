# 🏗️ Artitec Backend Development

The **Artitec Backend** is a scalable API built with **FastAPI**, **SQLAlchemy**, and **Pydantic**, designed to power the **Artitec Platform** — a modern real estate technology ecosystem connecting **Builders**, **Communities**, **Sales Reps**, and **Buyers**.  

It serves as the data and business logic backbone for Artitec’s SwiftUI front-end, providing endpoints for authentication, profiles, listings, communities, social interactions, and analytics. It now includes a robust social and messaging layer enabling follows, likes, comments, and direct messaging between platform users.

---

## 🚀 Features

- 🔐 **User Authentication** — Secure registration, login, and JWT-based sessions.  
- 👤 **Role-Based Profiles** — Modular design for Buyers, Builders, Community Admins, and Sales Reps, including social interactions (followers, likes, comments).  
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
│   │   ├── uploads.py        # /v1/uploads/avatars, media
│   │   ├── social.py         # /v1/social/ (follows, likes, comments)
│   │   ├── dm.py             # /v1/dm/ direct messaging
│   │   └── notifications.py  # /v1/notifications/ alerts
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
| **Builders** | `/v1/builders` | Builder portfolios, org details, awards, projects, and followers |
| **Communities** | `/v1/communities` | Community pages, admins, events, active builders, and followers |
| **Properties** | `/v1/properties` | Property listing creation, retrieval, and updates |
| **Posts** | `/v1/posts` | Feed posts, comments, and engagement |
| **Boards** | `/v1/boards` | Saved boards or collections of listings/builders |
| **Analytics** | `/v1/analytics` | Tracks property views, saves, and engagement metrics |
| **Uploads** | `/v1/uploads` | Media upload endpoints for images and files |
| **Social** | `/v1/social` | Follows, likes, comments, and feed interactions across builders, communities, and users |
| **DM** | `/v1/dm` | Direct messaging between users and builder reps |
| **Notifications** | `/v1/notifications` | Alerts for follows, likes, comments, and messages |

---

### 📣 Social & Messaging Layer
Artitec introduces a unified social graph supporting follows, likes, comments, and direct messages across all profile types.

| Feature | Base Path | Description |
|----------|------------|-------------|
| **Follows** | `/v1/social/follows` | Follow/unfollow builders, communities, or users |
| **Likes** | `/v1/social/likes` | Like or unlike posts, comments, and projects |
| **Comments** | `/v1/social/comments` | Threaded comments and replies on posts or profiles |
| **DM** | `/v1/dm` | One-on-one and group direct messaging |
| **Notifications** | `/v1/notifications` | Event-driven alerts for social interactions |

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

## 📜 Route Reference (v1)

> **Note on paths:** Builder profile endpoints live under `/v1/profiles/builders` (profile-focused). A convenience alias `/v1/builders` may be introduced later.

### 🔐 Auth — `/v1/auth`

| Method | Path | Description |
|---|---|---|
| POST | `/register` | Create an account |
| POST | `/login` | Obtain JWT access token |
| POST | `/refresh` | Refresh access token |

**Example**
```bash
curl -X POST "$BASE/v1/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@artitec.com","password":"pass"}'
```

---

### 🧱 Builder Profiles — `/v1/profiles/builders`

| Method | Path | Description |
|---|---|---|
| GET | `/` | List builders (search & filters) |
| GET | `/{org_id}` | Get one builder profile |
| POST | `/` | Create builder profile |
| PUT | `/{org_id}` | Replace builder profile |
| PATCH | `/{org_id}` | Update builder profile |
| DELETE | `/{org_id}` | Delete builder profile |

**Query params (list):**
- `q`: free text search (company/about/notes)
- `specialty`: filter by specialty (e.g., `Custom Homes`)
- `city`: filter by city
- `limit` (default 50, max 200), `offset` (default 0)

**Response model:** `BuilderProfileOut`
- Includes: core fields + `properties: [PropertyRef]`, `communities: [CommunityRef]`, `followers_count`, `is_following`

**Examples**
```bash
# list
curl "$BASE/v1/profiles/builders?q=custom&city=Houston&limit=20"

# get one
curl "$BASE/v1/profiles/builders/42"

# create
curl -X POST "$BASE/v1/profiles/builders" \
  -H 'Content-Type: application/json' \
  -d '{"org_id":42,"company_name":"Artitec Builders","specialties":["Custom Homes"],"city":"Houston"}'
```

**Relations**
- Builder ↔ Property (portfolio): managed via backend logic (association table `builder_portfolio`)
- Builder ↔ Community (active): via `builder_communities`

> Optional future endpoints to explicitly manage links:
> - `POST /v1/communities/{community_id}/builders/{org_id}` — link
> - `DELETE /v1/communities/{community_id}/builders/{org_id}` — unlink

---

### 🏘️ Communities — `/v1/communities`

| Method | Path | Description |
|---|---|---|
| GET | `/` | List communities |
| GET | `/{id}` | Get one community |
| POST | `/` | Create community |
| PATCH | `/{id}` | Update community |
| DELETE | `/{id}` | Delete community |
| GET | `/{id}/builders` | List active builders in the community |

**Response includes** (if implemented): `builders: [BuilderRef]`, `followers_count`, `is_following`

---

### 🏡 Properties — `/v1/properties`

| Method | Path | Description |
|---|---|---|
| GET | `/` | List & search properties |
| GET | `/{id}` | Get one property |
| POST | `/` | Create property |
| PATCH | `/{id}` | Update property |
| DELETE | `/{id}` | Delete property |

**Typical filters:** `q`, `city`, `min_price`, `max_price`, `beds`, `baths`, `status`

---

### 📣 Social — `/v1/social`

#### Follows — `/v1/social/follows`
| Method | Path | Description |
|---|---|---|
| POST | `/` | Follow a target |
| DELETE | `/` | Unfollow a target |
| GET | `/{target_type}/{target_id}/followers` | List followers |
| GET | `/users/{user_id}/following` | List what a user follows |

**Body (toggle):** `{ "target_type": "builder|community|user", "target_id": 123 }`

#### Likes — `/v1/social/likes`
| Method | Path | Description |
|---|---|---|
| POST | `/` | Like a target |
| DELETE | `/` | Unlike a target |
| GET | `/{target_type}/{target_id}` | List likes for a target |

**Body (toggle):** `{ "target_type": "post|comment|property|builder", "target_id": 987 }`

#### Comments — `/v1/social/comments`
| Method | Path | Description |
|---|---|---|
| POST | `/` | Create a comment/reply |
| GET | `/{target_type}/{target_id}` | List comments for a target |
| DELETE | `/{id}` | Soft delete a comment |

**Create body:** `{ "target_type": "post|builder|community|property", "target_id": 7, "parent_id": null, "body": "Nice work!" }`

---

### 💬 Direct Messaging — `/v1/dm`

| Method | Path | Description |
|---|---|---|
| POST | `/conversations` | Create a conversation (participants) |
| GET | `/conversations` | List conversations for current user |
| GET | `/conversations/{id}` | Get a conversation |
| POST | `/conversations/{id}/messages` | Send a message |
| GET | `/conversations/{id}/messages` | List messages (cursor) |
| POST | `/conversations/{id}/read` | Mark last read message |

**Create body:** `{ "participant_ids": [2,3] }`
**Send message:** `{ "body": "Hello!" }`

---

### 🔔 Notifications — `/v1/notifications`

| Method | Path | Description |
|---|---|---|
| GET | `/` | List current user notifications |
| POST | `/read` | Mark notifications read (ids or up-to timestamp) |