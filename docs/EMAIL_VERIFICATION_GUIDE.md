# Email Verification System - Implementation Guide

**Created:** November 12, 2024
**Status:** ✅ Complete and Ready for Testing

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Database Schema](#database-schema)
4. [API Endpoints](#api-endpoints)
5. [Email Configuration](#email-configuration)
6. [Frontend Integration](#frontend-integration)
7. [Testing](#testing)
8. [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

The email verification system ensures users verify their email address after registration, improving account security and enabling password recovery.

### Features

✅ Automatic verification email on registration
✅ Secure tokens with 48-hour expiration
✅ One-time use tokens
✅ Beautiful HTML email templates with brand styling
✅ Console mode for development (no SMTP needed)
✅ Resend verification email functionality
✅ SwiftUI views for iOS integration
✅ Deep linking support for email verification

---

## 🏗️ Architecture

### Flow Diagram

```
User Registers
     ↓
Generate Token
     ↓
Save to DB
     ↓
Send Email
     ↓
User Clicks Link
     ↓
/verify-email
     ↓
Validate Token
     ↓
Mark Email Verified
     ↓
Mark Token Used
```

### Components

1. **Database Table:** `email_verifications` (already exists)
2. **SQLAlchemy Model:** `model/user.py::EmailVerification`
3. **API Routes:** `routes/email_verification.py`
4. **Email Service:** `src/email_service.py::send_email_verification()`
5. **iOS Service:** `Core/Auth/EmailVerificationService.swift`
6. **iOS Views:** `Features/Auth/EmailVerificationView.swift`

---

## 💾 Database Schema

### email_verifications Table

```sql
CREATE TABLE email_verifications (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    token CHAR(64) UNIQUE NOT NULL,
    expires_at DATETIME NOT NULL,
    used_at DATETIME NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX ix_email_verifications_user_id (user_id)
);
```

### users Table (Relevant Field)

```sql
is_email_verified BOOLEAN NOT NULL DEFAULT 0
```

---

## 🌐 API Endpoints

### 1. Verify Email

**POST** `/v1/auth/verify-email`

Verify email address using token from verification email.

**Request Body:**
```json
{
  "token": "a1b2c3d4e5f6g7h8..."
}
```

**Response:** `200 OK`
```json
{
  "message": "Email address verified successfully! You can now access all features.",
  "email_verified": true
}
```

**Error Responses:**

**400 Bad Request** - Invalid/expired token:
```json
{
  "detail": "Invalid or expired verification token"
}
```

**400 Bad Request** - Token already used:
```json
{
  "detail": "This verification link has already been used"
}
```

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/v1/auth/verify-email" \
  -H "Content-Type: application/json" \
  -d '{"token":"your-token-here"}'
```

---

### 2. Resend Verification Email

**POST** `/v1/auth/resend-verification`

Request a new verification email.

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Response:** `200 OK`
```json
{
  "message": "If an unverified account exists with that email, a verification link has been sent."
}
```

**Notes:**
- Always returns success (prevents email enumeration)
- Invalidates previous unused tokens
- Only sends if user exists and is not verified
- Token expires in 48 hours

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/v1/auth/resend-verification" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com"}'
```

---

### 3. Check Verification Status

**GET** `/v1/auth/check-verification-status/{email}`

Check if an email address is verified.

**Response:** `200 OK`
```json
{
  "email": "user@example.com",
  "is_verified": true
}
```

**Note:** This endpoint reveals if an email exists. Consider adding authentication.

---

## 📧 Email Configuration

### Environment Variables

Uses the same configuration as password reset:

```bash
# Email Configuration (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@artitec.com
FROM_NAME=Artitec

# Frontend URL (for verification links)
FRONTEND_URL=http://localhost:3000
```

### Console Mode (Development)

If SMTP credentials are not configured, emails print to console:

```
================================================================================
📧 EMAIL (Console Mode)
================================================================================
To: user@example.com
From: Artitec <noreply@artitec.com>
Subject: Verify Your Artitec Email Address
Time: 2024-11-12T15:30:00
--------------------------------------------------------------------------------
[HTML email content with verification link]
================================================================================
```

---

## 🎨 Frontend Integration

### Backend Flow

1. **During Registration** (`routes/auth.py`):
   ```python
   # Token is automatically created
   ver = EmailVerification(
       user_id=u.id,
       token=gen_token_hex(32),
       expires_at=datetime.utcnow() + timedelta(days=2)
   )

   # Email is automatically sent
   email_service.send_email_verification(
       to_email=u.email,
       verification_token=ver.token,
       user_name=f"{u.first_name} {u.last_name}"
   )
   ```

2. **Response includes:**
   ```json
   {
     "user": {
       "email": "user@example.com",
       "is_email_verified": false,
       ...
     },
     "access_token": "...",
     "refresh_token": "...",
     "requires_email_verification": true
   }
   ```

### iOS/SwiftUI Flow

1. **After Registration** (`Features/Auth/AuthPage.swift`):
   ```swift
   if res.requires_email_verification == true && !user.is_email_verified {
       verificationEmail = user.email
       withAnimation(.easeInOut) { goToEmailVerification = true }
   }
   ```

2. **Email Verification View** shows:
   - User's email address
   - Instructions to check inbox
   - Resend button
   - Skip option ("I'll verify later")

3. **Deep Linking Support**:
   ```swift
   // Handle: artitec://verify-email?token=abc123
   EmailVerificationView(email: email, token: token)
   ```

### React Example

```jsx
// After successful registration
const handleRegister = async (userData) => {
  const response = await fetch('/v1/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(userData)
  });

  const data = await response.json();

  if (data.requires_email_verification) {
    // Navigate to email verification pending screen
    navigate('/verify-email', { state: { email: data.user.email } });
  }
};

// Verification page (from email link)
const VerifyEmailPage = () => {
  const token = new URLSearchParams(location.search).get('token');

  useEffect(() => {
    const verify = async () => {
      const response = await fetch('/v1/auth/verify-email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token })
      });

      if (response.ok) {
        // Show success, redirect to app
        navigate('/dashboard');
      }
    };

    if (token) verify();
  }, [token]);
};
```

---

## 🧪 Testing

### Manual Testing Flow

1. **Register a new account:**
   ```bash
   curl -X POST "http://localhost:8000/v1/auth/register" \
     -H "Content-Type: application/json" \
     -d '{
       "first_name":"Test",
       "last_name":"User",
       "email":"test@example.com",
       "password":"Password123",
       "confirm_password":"Password123",
       "Role":""
     }'
   ```

2. **Check console for verification email** (if in console mode):
   - Copy the token from the verification URL

3. **Verify the email:**
   ```bash
   curl -X POST "http://localhost:8000/v1/auth/verify-email" \
     -H "Content-Type: application/json" \
     -d '{"token":"YOUR_TOKEN_HERE"}'
   ```

4. **Check verification status:**
   ```bash
   curl "http://localhost:8000/v1/auth/check-verification-status/test@example.com"
   ```

5. **Test resend:**
   ```bash
   curl -X POST "http://localhost:8000/v1/auth/resend-verification" \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com"}'
   ```

### iOS Testing

1. Run the app in simulator
2. Register a new account
3. Email verification screen should appear automatically
4. Check backend console for verification email
5. Copy the token from the console output
6. Test deep link: `xcrun simctl openurl booted "artitec://verify-email?token=YOUR_TOKEN"`

---

## 🐛 Troubleshooting

### Email Not Sending

**Problem:** Verification emails not being sent

**Solutions:**
1. Check SMTP credentials in `.env`
2. Verify SMTP port (587 for TLS, 465 for SSL)
3. For Gmail, ensure App Password is used
4. Check console for error messages
5. In development, use console mode

### Token Not Found

**Problem:** "Invalid or expired verification token"

**Causes:**
1. Token already used (check `used_at` column)
2. Token expired (>48 hours old)
3. Token not in database
4. User was deleted

**Debug:**
```sql
-- Check token in database
SELECT * FROM email_verifications
WHERE token = 'YOUR_TOKEN_HERE';

-- Check if token is valid
SELECT
    token,
    expires_at,
    used_at,
    expires_at > NOW() as is_not_expired,
    used_at IS NULL as is_not_used
FROM email_verifications
WHERE token = 'YOUR_TOKEN_HERE';
```

### User Already Verified

**Problem:** User receives "already verified" message

**Solution:** This is expected behavior. Check:
```sql
SELECT email, is_email_verified
FROM users
WHERE email = 'user@example.com';
```

---

## ✅ Production Checklist

Before deploying to production:

- [ ] Set up real SMTP credentials
- [ ] Configure `FRONTEND_URL` to production domain
- [ ] Test with real email providers (Gmail, Outlook, Yahoo, etc.)
- [ ] Implement rate limiting on `/resend-verification`
- [ ] Add authentication to `/check-verification-status`
- [ ] Set up monitoring for failed emails
- [ ] Create automated tests
- [ ] Review and customize email templates
- [ ] Configure deep linking for iOS/Android
- [ ] Test email deliverability (check spam folders)
- [ ] Add email verification reminders (optional)

---

## 📚 Related Documentation

- [PASSWORD_RESET_GUIDE.md](PASSWORD_RESET_GUIDE.md) - Password reset system
- [COMPREHENSIVE_DOCUMENTATION.md](../COMPREHENSIVE_DOCUMENTATION.md) - Main docs
- [SWIFTUI_PASSWORD_RESET_GUIDE.md](SWIFTUI_PASSWORD_RESET_GUIDE.md) - iOS password reset

---

**Last Updated:** November 12, 2024
**Version:** 1.0.0
**Status:** ✅ Ready for Testing
