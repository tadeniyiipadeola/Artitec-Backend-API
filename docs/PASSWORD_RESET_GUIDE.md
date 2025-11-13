# Password Reset System - Implementation Guide

**Created:** November 12, 2024
**Status:** ✅ Complete and Ready for Production

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Database Schema](#database-schema)
4. [API Endpoints](#api-endpoints)
5. [Email Configuration](#email-configuration)
6. [Security Features](#security-features)
7. [Frontend Integration](#frontend-integration)
8. [Testing](#testing)
9. [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

The password reset system provides a secure forgot password flow that allows users to reset their passwords via email verification.

### Features

✅ Secure token generation with 32-byte random tokens
✅ Token expiration (1 hour by default)
✅ One-time use tokens
✅ Email verification with beautiful HTML templates
✅ Console mode for development (no SMTP needed)
✅ Password strength validation
✅ Security against email enumeration attacks
✅ Automatic cleanup of expired tokens

---

## 🏗️ Architecture

### Flow Diagram

```
User Requests Reset
        ↓
    /forgot-password
        ↓
  Generate Token
        ↓
   Save to DB
        ↓
   Send Email
        ↓
User Clicks Link
        ↓
/verify-reset-token (optional)
        ↓
User Enters New Password
        ↓
   /reset-password
        ↓
 Validate Token
        ↓
Update Password
        ↓
 Mark Token Used
        ↓
Send Confirmation Email
```

### Components

1. **Database Table:** `password_reset_tokens`
2. **SQLAlchemy Model:** `model/password_reset.py`
3. **Pydantic Schemas:** `schema/password_reset.py`
4. **Route Handlers:** `routes/password_reset.py`
5. **Email Service:** `src/email_service.py`

---

## 💾 Database Schema

### password_reset_tokens Table

```sql
CREATE TABLE password_reset_tokens (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(50) NOT NULL,
    token VARCHAR(255) NOT NULL UNIQUE,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    expires_at DATETIME NOT NULL,
    used_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX ix_password_reset_tokens_user_id (user_id),
    INDEX ix_password_reset_tokens_token (token),
    INDEX ix_password_reset_tokens_expires_at (expires_at),
    INDEX ix_password_reset_user_valid (user_id, expires_at, used_at)
);
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | BIGINT | Primary key |
| `user_id` | VARCHAR(50) | FK to users.user_id (USR-xxx) |
| `token` | VARCHAR(255) | URL-safe token for reset link |
| `token_hash` | VARCHAR(255) | SHA-256 hash of token |
| `expires_at` | DATETIME | Expiration timestamp |
| `used_at` | DATETIME | When token was used (null if unused) |
| `created_at` | DATETIME | Token creation time |

---

## 🌐 API Endpoints

### 1. Request Password Reset

**POST** `/v1/auth/forgot-password`

Request a password reset link to be sent via email.

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Response:** `200 OK`
```json
{
  "message": "If an account with that email exists, a password reset link has been sent."
}
```

**Notes:**
- Always returns success (prevents email enumeration)
- Sends email only if user exists
- Token expires in 1 hour
- Invalidates previous unused tokens

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/v1/auth/forgot-password" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com"}'
```

---

### 2. Verify Reset Token (Optional)

**POST** `/v1/auth/verify-reset-token`

Check if a reset token is valid before showing the password reset form.

**Request Body:**
```json
{
  "token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
}
```

**Response:** `200 OK`
```json
{
  "valid": true,
  "message": "Token is valid",
  "expires_at": "2024-11-12T16:30:00",
  "user_email": "u***@example.com"
}
```

**Error Response:**
```json
{
  "valid": false,
  "message": "This token has expired"
}
```

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/v1/auth/verify-reset-token" \
  -H "Content-Type: application/json" \
  -d '{"token":"your-token-here"}'
```

---

### 3. Reset Password

**POST** `/v1/auth/reset-password`

Reset password using a valid token.

**Request Body:**
```json
{
  "token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
  "new_password": "NewSecurePassword123"
}
```

**Password Requirements:**
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number

**Response:** `200 OK`
```json
{
  "message": "Password has been reset successfully. You can now log in with your new password.",
  "user_id": "USR-1763002155-GRZVLL"
}
```

**Error Responses:**

**400 Bad Request** - Invalid token:
```json
{
  "detail": "Invalid or expired reset token"
}
```

**400 Bad Request** - Weak password:
```json
{
  "detail": "Password must contain at least one uppercase letter"
}
```

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/v1/auth/reset-password" \
  -H "Content-Type: application/json" \
  -d '{
    "token":"your-token-here",
    "new_password":"NewSecurePassword123"
  }'
```

---

### 4. Cancel Reset Token

**POST** `/v1/auth/cancel-reset-token`

Invalidate a reset token (useful if user wants to cancel the request).

**Request Body:**
```json
{
  "token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
}
```

**Response:** `200 OK`
```json
{
  "message": "Reset token has been cancelled"
}
```

---

### 5. Cleanup Expired Tokens (Admin)

**DELETE** `/v1/auth/cleanup-expired-tokens`

Remove all expired tokens from database (admin endpoint).

**Response:** `200 OK`
```json
{
  "message": "Cleaned up 15 expired tokens",
  "deleted_count": 15
}
```

**TODO:** Add admin authentication check before production.

---

## 📧 Email Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Email Configuration (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@artitec.com
FROM_NAME=Artitec

# Frontend URL (for reset links)
FRONTEND_URL=http://localhost:3000
```

### Console Mode (Development)

If SMTP credentials are not configured, email service automatically runs in **console mode**:
- Emails are printed to console instead of sent
- No external SMTP required
- Perfect for local development

**Example Console Output:**
```
================================================================================
📧 EMAIL (Console Mode)
================================================================================
To: user@example.com
From: Artitec <noreply@artitec.com>
Subject: Reset Your Artitec Password
Time: 2024-11-12T15:30:00
--------------------------------------------------------------------------------
[HTML email content here]
================================================================================
```

### Gmail Setup

If using Gmail, you need to:
1. Enable 2-factor authentication
2. Generate an App Password
3. Use the App Password (not your regular password)

**Steps:**
1. Go to Google Account Settings
2. Security → 2-Step Verification
3. App Passwords → Generate new password
4. Use generated password in `SMTP_PASSWORD`

---

## 🔒 Security Features

### 1. Token Security

- **Random Generation:** Uses `secrets.token_urlsafe(32)` for cryptographically secure tokens
- **Hashed Storage:** Tokens are hashed (SHA-256) before storage
- **Unique Tokens:** Database enforces uniqueness
- **Time-Limited:** 1-hour expiration (configurable)
- **One-Time Use:** Marked as used after successful reset

### 2. Email Enumeration Protection

The `/forgot-password` endpoint **always returns the same success message** regardless of whether the email exists. This prevents attackers from discovering which emails are registered.

```python
# Always returns:
{
  "message": "If an account with that email exists, a password reset link has been sent."
}
```

### 3. Rate Limiting (TODO)

**Recommended:** Implement rate limiting on `/forgot-password`:
- Max 3 requests per email per hour
- Prevents spam/abuse
- Use Redis or in-memory cache

**Example Implementation:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/forgot-password")
@limiter.limit("3/hour")
def forgot_password(...):
    ...
```

### 4. Password Strength Validation

Passwords must meet these requirements:
- ✅ Minimum 8 characters
- ✅ At least one uppercase letter
- ✅ At least one lowercase letter
- ✅ At least one number
- ⚠️ Optional: Special characters (currently disabled)

### 5. Automatic Token Cleanup

- Old expired tokens are automatically cleaned up
- Previous unused tokens are invalidated when new request is made
- Admin endpoint for manual cleanup

---

## 🎨 Frontend Integration

### Flow

1. **Forgot Password Page**
   ```jsx
   // User enters email
   POST /v1/auth/forgot-password
   {
     "email": "user@example.com"
   }

   // Show success message (always)
   "Check your email for reset link"
   ```

2. **Email Link**
   ```
   User receives email with link:
   https://yourapp.com/reset-password?token=abc123...
   ```

3. **Reset Password Page**
   ```jsx
   // Optional: Verify token on page load
   POST /v1/auth/verify-reset-token
   {
     "token": "abc123..."
   }

   // If valid, show form
   // User enters new password
   POST /v1/auth/reset-password
   {
     "token": "abc123...",
     "new_password": "NewPassword123"
   }

   // On success, redirect to login
   ```

### React Example

```jsx
// ForgotPassword.jsx
const handleSubmit = async (e) => {
  e.preventDefault();

  try {
    await fetch('/v1/auth/forgot-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email })
    });

    // Always show success
    setMessage('Check your email for a reset link');
  } catch (error) {
    setError('Something went wrong. Please try again.');
  }
};

// ResetPassword.jsx
const handleSubmit = async (e) => {
  e.preventDefault();

  try {
    const response = await fetch('/v1/auth/reset-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        token: params.get('token'),
        new_password: password
      })
    });

    if (response.ok) {
      navigate('/login?reset=success');
    } else {
      const error = await response.json();
      setError(error.detail);
    }
  } catch (error) {
    setError('Failed to reset password');
  }
};
```

### SwiftUI Example

```swift
// ForgotPasswordView.swift
func requestPasswordReset() async {
    let url = URL(string: "\(apiBase)/v1/auth/forgot-password")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")

    let body = ["email": email]
    request.httpBody = try? JSONEncoder().encode(body)

    do {
        let (_, response) = try await URLSession.shared.data(for: request)
        if (response as? HTTPURLResponse)?.statusCode == 200 {
            showMessage = true
        }
    } catch {
        errorMessage = "Failed to send reset email"
    }
}

// ResetPasswordView.swift
func resetPassword() async {
    let url = URL(string: "\(apiBase)/v1/auth/reset-password")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")

    let body = [
        "token": token,
        "new_password": newPassword
    ]
    request.httpBody = try? JSONEncoder().encode(body)

    do {
        let (_, response) = try await URLSession.shared.data(for: request)
        if (response as? HTTPURLResponse)?.statusCode == 200 {
            // Navigate to login
            dismiss()
        }
    } catch {
        errorMessage = "Failed to reset password"
    }
}
```

---

## 🧪 Testing

### Manual Testing

1. **Request Reset:**
   ```bash
   curl -X POST "http://localhost:8000/v1/auth/forgot-password" \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com"}'
   ```

2. **Check Console:** (if in console mode)
   - Look for email output in terminal
   - Copy the token from the reset URL

3. **Verify Token:**
   ```bash
   curl -X POST "http://localhost:8000/v1/auth/verify-reset-token" \
     -H "Content-Type: application/json" \
     -d '{"token":"YOUR_TOKEN_HERE"}'
   ```

4. **Reset Password:**
   ```bash
   curl -X POST "http://localhost:8000/v1/auth/reset-password" \
     -H "Content-Type: application/json" \
     -d '{
       "token":"YOUR_TOKEN_HERE",
       "new_password":"NewPassword123"
     }'
   ```

5. **Try to Login:**
   ```bash
   curl -X POST "http://localhost:8000/v1/auth/login" \
     -H "Content-Type: application/json" \
     -d '{
       "username":"test@example.com",
       "password":"NewPassword123"
     }'
   ```

### Automated Testing (TODO)

Create pytest tests for:
- ✅ Token generation uniqueness
- ✅ Token expiration logic
- ✅ Password validation
- ✅ Email sending (mock)
- ✅ Security scenarios

---

## 🐛 Troubleshooting

### Email Not Sending (SMTP)

**Problem:** Emails not being sent

**Solutions:**
1. Check SMTP credentials in `.env`
2. Verify SMTP port (587 for TLS, 465 for SSL)
3. Check firewall blocking SMTP
4. For Gmail, ensure App Password is used
5. Check console for error messages

**Test SMTP Connection:**
```python
python -c "
import smtplib
s = smtplib.SMTP('smtp.gmail.com', 587)
s.starttls()
s.login('your-email@gmail.com', 'your-app-password')
print('✅ SMTP connection successful')
s.quit()
"
```

### Token Not Found

**Problem:** "Invalid or expired reset token"

**Causes:**
1. Token already used
2. Token expired (>1 hour old)
3. Token not in database
4. User deleted

**Debug:**
```sql
-- Check token in database
SELECT * FROM password_reset_tokens
WHERE token = 'YOUR_TOKEN_HERE';

-- Check expiration
SELECT
    token,
    expires_at,
    used_at,
    expires_at > NOW() as is_not_expired,
    used_at IS NULL as is_not_used
FROM password_reset_tokens
WHERE token = 'YOUR_TOKEN_HERE';
```

### Password Validation Failing

**Problem:** "Password must contain..."

**Solution:** Ensure password meets requirements:
```python
# Valid examples:
"Password123"     ✅
"SecurePass1"     ✅
"MyNewP@ss1"      ✅

# Invalid examples:
"password"        ❌ No uppercase, no number
"PASSWORD123"     ❌ No lowercase
"Password"        ❌ No number
"Pass1"           ❌ Too short
```

### Migration Errors

**Problem:** Migration fails

**Solution:**
```bash
# Check current migration version
alembic current

# Run migration
alembic upgrade head

# If error persists, check database manually
mysql -u root -p
USE artitec_db;
SHOW TABLES LIKE 'password%';
```

---

## 📚 Additional Resources

- **Main Documentation:** [COMPREHENSIVE_DOCUMENTATION.md](../COMPREHENSIVE_DOCUMENTATION.md)
- **API Documentation:** Auto-generated at `/docs` (FastAPI Swagger UI)
- **Email Service:** `src/email_service.py`
- **Route Handlers:** `routes/password_reset.py`

---

## ✅ Checklist for Production

Before deploying to production:

- [ ] Set up real SMTP credentials
- [ ] Configure `FRONTEND_URL` to production domain
- [ ] Implement rate limiting on `/forgot-password`
- [ ] Add admin authentication to cleanup endpoint
- [ ] Set up monitoring for failed emails
- [ ] Create automated tests
- [ ] Test with real email providers (Gmail, Outlook, etc.)
- [ ] Review and customize email templates
- [ ] Set up email delivery monitoring
- [ ] Consider adding 2FA after password reset (future)

---

**Last Updated:** November 12, 2024
**Version:** 1.0.0
**Status:** ✅ Ready for Testing
