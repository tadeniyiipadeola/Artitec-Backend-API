# 🏗️ Artitec Backend - Comprehensive Documentation

**Version:** 2.0
**Last Updated:** 2024-11-12
**Status:** Production Ready

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Recent Major Updates](#recent-major-updates)
3. [Architecture](#architecture)
4. [Database Schema](#database-schema)
5. [API Reference](#api-reference)
6. [Development Setup](#development-setup)
7. [Migration Guide](#migration-guide)
8. [iOS/SwiftUI Integration](#iosswiftui-integration)
9. [Todo & Future Plans](#todo--future-plans)

---

## 🎯 Project Overview

The **Artitec Backend** is a scalable RESTful API built with **FastAPI**, **SQLAlchemy**, and **Pydantic**, designed to power the **Artitec Platform** — a modern real estate technology ecosystem connecting **Builders**, **Communities**, **Sales Reps**, and **Buyers**.

### Core Features

- 🔐 **JWT Authentication** - Secure registration, login, and token-based sessions
- 👤 **Role-Based Profiles** - Modular design for Buyers, Builders, Community Admins, and Sales Reps
- 🏡 **Property Management** - Full CRUD for listings, media, and portfolios
- 🏘️ **Community Integration** - HOA/Community pages, admins, events, amenities
- 💬 **Social Features** - Follows, likes, comments, and direct messaging
- 📊 **Analytics** - Track views, saves, and engagement metrics
- ☁️ **Media Uploads** - Support for avatars, logos, and property images

### Technology Stack

- **Framework:** FastAPI (Python 3.11+)
- **ORM:** SQLAlchemy 2.0
- **Validation:** Pydantic v2
- **Database:** MySQL/MariaDB
- **Migration:** Alembic
- **Authentication:** JWT (python-jose)
- **Deployment:** Docker, Synology NAS

---

## 🚀 Recent Major Updates

### ✅ Typed ID Migration (Nov 2024)

Successfully migrated from generic `public_id` to typed IDs across all entities:

**Column Renames:**
- `users.public_id` → `users.user_id` (USR-xxx)
- `buyer_profiles.public_id` → `buyer_profiles.buyer_id` (BYR-xxx)
- `builder_profiles.public_id` → `builder_profiles.builder_id` (BLD-xxx)
- `communities.public_id` → `communities.community_id` (CMY-xxx)
- `sales_reps.public_id` → `sales_rep_id` (SLS-xxx)
- `community_admin_profiles.public_id` → `community_admin_id` (CAP-xxx)

**Foreign Key Updates:**
- All `user_id` foreign keys converted from INTEGER → VARCHAR(50)
- Now reference `users.user_id` (string) instead of `users.id` (integer)
- Updated all SQLAlchemy models, Pydantic schemas, and route handlers

**Benefits:**
- ✅ Self-documenting IDs with type prefixes
- ✅ Easier debugging and log analysis
- ✅ Better API responses with meaningful identifiers
- ✅ Consistent ID format across all entities

### ✅ Role System Refactor (2024)

Simplified role management:
- Removed `role_id` foreign key from users table
- Changed to direct string role field: `role VARCHAR(50)`
- Values: "buyer", "builder", "community", "community_admin", "salesrep", "admin"
- Updated all authentication and authorization logic

### ✅ Community Admin Profile System (2024)

Complete community management infrastructure:
- 9 database tables for comprehensive community profiles
- Full CRUD API endpoints for community admin operations
- User-to-community linking via `community_admin_profiles`
- Support for amenities, events, awards, discussion threads, phases

---

## 🏛️ Architecture

### Project Structure

```
Artitec Backend Development/
├── alembic/                    # Database migrations
│   └── versions/               # Migration files
├── config/
│   ├── db.py                   # Database connection & session
│   └── security.py             # JWT auth, password hashing
├── model/
│   ├── user.py                 # Users, Role models
│   └── profiles/
│       ├── buyer.py            # BuyerProfile, BuyerTour, BuyerDocument
│       ├── builder.py          # BuilderProfile
│       ├── community.py        # Community + 8 related tables
│       ├── community_admin_profile.py
│       └── sales_rep.py        # SalesRep
├── schema/
│   ├── auth.py                 # Auth schemas, role forms
│   ├── user.py                 # UserOut, UserBase
│   ├── buyers.py               # Buyer schemas
│   ├── builder.py              # Builder schemas
│   ├── community.py            # Community schemas
│   ├── sales_rep.py            # Sales rep schemas
│   └── property.py             # Property schemas
├── routes/
│   ├── auth.py                 # Registration, login, role selection
│   ├── user.py                 # User endpoints
│   ├── admin_helpers.py        # Admin utilities
│   └── profiles/
│       ├── buyers.py           # Buyer profile routes
│       ├── buyers_updated.py   # New buyer routes (recommended)
│       ├── builder.py          # Builder profile routes
│       ├── community.py        # Community routes
│       ├── community_admin.py  # Community admin routes
│       └── sales_rep.py        # Sales rep routes
├── src/
│   ├── id_generator.py         # Typed ID generation (USR-, BYR-, etc.)
│   ├── route_helpers.py        # Common lookup functions
│   └── schemas.py              # Shared schema imports
├── scripts/
│   ├── create_full_community_profile.py
│   └── create_community_admin_sample.py
└── docs/
    └── SWIFTUI_IMPLEMENTATION_GUIDE.md
```

### Design Principles

1. **Versioned APIs** - All endpoints under `/v1/` for maintainability
2. **Service Layer Separation** - Route logic stays thin
3. **Modular Roles** - Separate tables and schemas per user type
4. **Strong Type Safety** - Pydantic validation on all I/O
5. **Foreign Key Integrity** - Cascade deletes, proper constraints
6. **Scalability First** - Designed to expand with microservices

---

## 🗄️ Database Schema

### Core Tables

#### Users Table
```sql
users
├─ id (BIGINT UNSIGNED) - PRIMARY KEY - Internal DB ID
├─ user_id (VARCHAR(50)) - UNIQUE - External API identifier (USR-xxx)
├─ email (VARCHAR(255)) - UNIQUE
├─ first_name, last_name (VARCHAR)
├─ phone_e164 (VARCHAR) - E.164 format phone
├─ password_hash (VARCHAR)
├─ role (VARCHAR(50)) - Direct role string
├─ plan_tier (VARCHAR) - "free", "pro", "enterprise"
├─ onboarding_completed (BOOLEAN)
├─ is_email_verified (BOOLEAN)
├─ status (VARCHAR) - "active", "suspended", "deleted"
├─ created_at, updated_at (TIMESTAMP)
```

#### Profile Tables

**BuyerProfile** (1-to-1 with User)
```sql
buyer_profiles
├─ id (BIGINT UNSIGNED) - PK
├─ buyer_id (VARCHAR(50)) - UNIQUE - BYR-xxx
├─ user_id (VARCHAR(50)) - FK → users.user_id - UNIQUE
├─ display_name, bio, location
├─ budget_min_usd, budget_max_usd
├─ financing_status, loan_program
└─ (many more buyer-specific fields)
```

**BuilderProfile** (1-to-1 with User)
```sql
builder_profiles
├─ id (BIGINT UNSIGNED) - PK
├─ builder_id (VARCHAR(50)) - UNIQUE - BLD-xxx
├─ user_id (VARCHAR(50)) - FK → users.user_id - UNIQUE
├─ name, website, about
├─ specialties (JSON array)
├─ rating (DECIMAL)
├─ verified (TINYINT)
└─ communities_served (JSON array)
```

**Community** (Entity, not a user profile)
```sql
communities
├─ id (BIGINT UNSIGNED) - PK
├─ community_id (VARCHAR(64)) - UNIQUE - CMY-xxx
├─ user_id (VARCHAR(50)) - FK → users.user_id - NULLABLE (owner)
├─ name, city, state, postal_code
├─ followers, residents, homes
├─ about, intro_video_url
├─ is_verified (BOOLEAN)
├─ founded_year, development_stage
└─ 8 related tables (amenities, events, builder_cards, admins, awards, topics, phases)
```

**CommunityAdminProfile** (Links users to communities)
```sql
community_admin_profiles
├─ id (BIGINT UNSIGNED) - PK
├─ community_admin_id (VARCHAR(50)) - UNIQUE - CAP-xxx
├─ user_id (VARCHAR(50)) - FK → users.user_id - UNIQUE
├─ community_id (BIGINT) - FK → communities.id
├─ first_name, last_name, title
├─ contact_email, contact_phone
├─ can_post_announcements, can_manage_events, can_moderate_threads
└─ extra (JSON)
```

**SalesRep** (Can be employee or user-linked)
```sql
sales_reps
├─ id (BIGINT UNSIGNED) - PK
├─ sales_rep_id (VARCHAR(50)) - UNIQUE - SLS-xxx
├─ user_id (VARCHAR(50)) - FK → users.user_id - NULLABLE
├─ builder_id (BIGINT) - FK → builder_profiles.id
├─ community_id (BIGINT) - FK → communities.id - NULLABLE
├─ full_name, email, phone
├─ avatar_url, region, office_address
└─ verified (BOOLEAN)
```

### Relationships

```
User (1) ──────── (1) BuyerProfile
User (1) ──────── (1) BuilderProfile
User (1) ──────── (1) CommunityAdminProfile ──── (1) Community
BuilderProfile (1) ──── (N) SalesRep
BuilderProfile (M) ──── (N) Community (via builder_communities)
BuilderProfile (M) ──── (N) Property (via builder_portfolio)
```

---

## 🌐 API Reference

### Authentication Endpoints

**Base Path:** `/v1/auth`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/register` | Create new user account |
| POST | `/login` | Login and receive JWT token |
| POST | `/logout` | Logout (invalidate token) |
| POST | `/role-selection` | Select user role and plan |
| POST | `/role-form/preview` | Preview role form submission |
| POST | `/role-form/commit` | Commit role and create profile |

**Example Registration:**
```bash
curl -X POST "http://localhost:8000/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePass123",
    "first_name": "John",
    "last_name": "Doe",
    "phone_e164": "+14155551234"
  }'
```

**Example Login:**
```bash
curl -X POST "http://localhost:8000/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john@example.com",
    "password": "SecurePass123"
  }'
```

### User Endpoints

**Base Path:** `/v1/users`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/me` | Get current authenticated user |
| GET | `/{user_id}` | Get user by user_id (USR-xxx) |
| PATCH | `/me/role` | Update own role |
| PATCH | `/{user_id}/role` | Update user role (admin only) |

### Buyer Profile Endpoints

**Recommended Base Path:** `/v1/buyers`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/{buyer_id}` | Get buyer by buyer_id (BYR-xxx) |
| PATCH | `/{buyer_id}` | Update buyer profile |
| DELETE | `/{buyer_id}` | Delete buyer profile |
| GET | `/{buyer_id}/tours` | List buyer's property tours |
| POST | `/{buyer_id}/tours` | Create tour |

**Legacy Endpoints:** `/v1/users/{user_id}/buyer` (for backward compatibility)

### Builder Profile Endpoints

**Base Path:** `/v1/profiles/builders`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List all builders (with search/filters) |
| GET | `/{user_id}` | Get builder by user_id (USR-xxx) |
| POST | `/` | Create builder profile |
| PATCH | `/{user_id}` | Update builder profile |
| DELETE | `/{user_id}` | Delete builder profile |
| GET | `/{user_id}/sales-reps` | List builder's sales reps |
| POST | `/{user_id}/sales-reps` | Create sales rep |

**Query Parameters (List):**
- `q` - Free text search (name, about, specialties)
- `city` - Filter by city
- `specialty` - Filter by specialty
- `limit` - Results per page (default: 50, max: 200)
- `offset` - Pagination offset

### Community Endpoints

**Base Path:** `/v1/communities`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List all communities |
| GET | `/{id}` | Get community by ID |
| GET | `/for-user/{user_id}` | Get community for a user |
| POST | `/` | Create community |
| PATCH | `/{id}` | Update community |
| DELETE | `/{id}` | Delete community |

**Query Parameter:**
- `include` - Comma-separated list: `amenities,events,builder_cards,admins,awards,threads,phases`

**Example:**
```bash
curl "http://localhost:8000/v1/communities/1?include=amenities,events,admins"
```

### Community Admin Endpoints

**Base Path:** `/v1/profiles/community-admins`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/me` | Get current user's community admin profile |
| GET | `/{id}` | Get by profile ID |
| GET | `/user/{user_id}` | Get by user_id (USR-xxx) |
| POST | `/` | Create community admin profile |
| PATCH | `/{id}` | Update profile |
| DELETE | `/{id}` | Delete profile |

### Property Endpoints

**Base Path:** `/v1/properties`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List properties (with filters) |
| GET | `/{id}` | Get property by ID |
| POST | `/` | Create property |
| PATCH | `/{id}` | Update property |
| DELETE | `/{id}` | Delete property |

**Filters:**
- `q` - Search query
- `city`, `state` - Location filters
- `min_price`, `max_price` - Price range
- `bedrooms`, `bathrooms` - Specifications
- `builder_id`, `community_id` - Relationship filters

### Social Endpoints

**Base Path:** `/v1/social`

| Feature | Endpoint | Description |
|---------|----------|-------------|
| **Follows** | POST `/follows` | Follow a user/builder/community |
|  | DELETE `/follows` | Unfollow |
|  | GET `/followers/{user_id}` | List followers |
|  | GET `/following/{user_id}` | List following |
| **Likes** | POST `/likes` | Like a post/comment |
|  | DELETE `/likes` | Unlike |
| **Comments** | POST `/comments` | Create comment |
|  | GET `/comments/{target_type}/{target_id}` | List comments |

---

## 🔧 Development Setup

### Prerequisites

- Python 3.11+
- MySQL/MariaDB 8.0+
- pip or poetry for dependency management

### Local Installation

```bash
# Clone repository
git clone https://github.com/artitec-tech/backend.git
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your database credentials

# Run migrations
alembic upgrade head

# Start development server
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Environment Variables

Create `.env` file with:

```bash
# Database
DB_HOST=localhost
DB_USER=artitec_user
DB_PASSWORD=your_password
DB_NAME=artitec_db
DB_PORT=3306

# JWT
JWT_SECRET=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Optional
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-west-2
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_auth.py

# Run with coverage
pytest --cov=app tests/
```

---

## 📦 Migration Guide

### Recent Migrations

#### Typed ID Migration (Nov 2024)

**Migration Files:**
1. `43f361179508_rename_public_id_to_typed_ids.py` - Renamed columns
2. `396dd510e408_add_user_id_to_sales_reps.py` - Added user_id to sales_reps
3. `e1393a7f6239_convert_user_id_fks_to_string.py` - Converted FKs to VARCHAR
4. `bc3b0a6a067f_fix_community_admin_profiles_user_id.py` - Fixed constraints

**To Apply:**
```bash
alembic upgrade head
```

**Rollback (if needed):**
```bash
alembic downgrade -1  # Roll back one migration
alembic downgrade 43f361179508  # Roll back to specific migration
```

#### Data Migration Notes

The typed ID migration preserves all existing data by:
1. Creating temporary columns for new VARCHAR user_ids
2. Migrating data using JOIN queries to copy string IDs
3. Dropping old integer columns
4. Renaming temp columns to final names
5. Recreating foreign key constraints

**No data loss** occurred during migration.

---

## 📱 iOS/SwiftUI Integration

### Key Changes for iOS Developers

#### Updated Field Names

All models now use typed IDs instead of generic `public_id`:

**Swift Model Example:**
```swift
struct BuyerProfile: Codable, Identifiable {
    let id: String              // Maps to buyer_id
    let buyerId: String         // Maps to buyer_id (duplicate for clarity)
    let userId: String          // Maps to user_id (STRING, not Int!)
    let displayName: String?
    let email: String?
    // ... other fields

    enum CodingKeys: String, CodingKey {
        case id = "buyer_id"
        case buyerId = "buyer_id"
        case userId = "user_id"
        case displayName = "display_name"
        case email
    }
}
```

**Important:** `user_id` is now a **String** (USR-xxx), not an integer!

#### Field Mapping Reference

| Swift Property | Backend Field | Type | Example |
|---|---|---|---|
| `id` | `buyer_id` | String | "BYR-1699564234-A7K9M2" |
| `userId` | `user_id` | String | "USR-1763002155-GRZVLL" |
| `builderId` | `builder_id` | String | "BLD-1699564234-X3P8Q1" |
| `communityId` | `community_id` | String | "CMY-1699564234-Z5R7N4" |

### Updated Endpoints

Change URL patterns in your iOS networking code:

**Before:**
```swift
// Old endpoint
GET /v1/users/USR-123/buyer
```

**After:**
```swift
// New endpoint (recommended)
GET /v1/buyers/BYR-456

// Legacy endpoint (still supported)
GET /v1/users/USR-123/buyer
```

### Complete Guide

See `docs/SWIFTUI_IMPLEMENTATION_GUIDE.md` for comprehensive iOS integration documentation.

---

## 📝 Todo & Future Plans

### High Priority

- [ ] **API Testing Suite**
  - [ ] Complete unit tests for all endpoints
  - [ ] Integration tests for complex flows
  - [ ] Load testing for production readiness

- [ ] **Documentation**
  - [ ] OpenAPI/Swagger documentation auto-generation
  - [ ] Postman collection for all endpoints
  - [ ] Video tutorials for common workflows

- [ ] **Performance Optimization**
  - [ ] Add Redis caching layer
  - [ ] Optimize N+1 queries with eager loading
  - [ ] Implement pagination on all list endpoints

### Medium Priority

- [ ] **Enhanced Features**
  - [ ] Real-time notifications (WebSocket)
  - [ ] Advanced search with Elasticsearch
  - [ ] Image optimization and CDN integration
  - [ ] Rate limiting and API throttling

- [ ] **Security Enhancements**
  - [ ] Two-factor authentication (2FA)
  - [ ] OAuth integration (Google, Apple)
  - [ ] API key management for third-party access
  - [ ] Audit logging for sensitive operations

- [ ] **Admin Dashboard**
  - [ ] Web-based admin panel
  - [ ] User management UI
  - [ ] Analytics and reporting
  - [ ] Content moderation tools

### Low Priority (Future Enhancements)

- [ ] Microservices architecture (split by domain)
- [ ] GraphQL endpoint alongside REST
- [ ] Machine learning recommendations
- [ ] Mobile SDK for React Native
- [ ] Plugin/extension system for third-party integrations

---

## 📞 Contact & Support

**Developed by:** Artitec Technology
**Lead Developer:** Samuel Adeniyi
**Email:** adeniyifamilia@gmail.com
**Website:** [https://woodbridgebungalow.lodgify.com](https://woodbridgebungalow.lodgify.com)

---

## 📄 License

Proprietary - All rights reserved by Artitec Technology

---

## 🙏 Acknowledgments

Built with modern best practices and designed for scalability, security, and developer experience.

**Key Technologies:**
- FastAPI for lightning-fast API performance
- SQLAlchemy for robust ORM capabilities
- Pydantic for bulletproof data validation
- Alembic for safe database migrations
- JWT for secure authentication

---

**Last Updated:** November 12, 2024
**Version:** 2.0.0
**Status:** ✅ Production Ready
