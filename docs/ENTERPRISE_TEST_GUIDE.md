# Enterprise Builder Test Guide

## Overview

This guide provides comprehensive testing instructions for the Artitec Enterprise Builder provisioning and multi-community team management features.

**Features Covered:**
- Enterprise builder provisioning (Phase 1)
- Multi-community team management (Phase 2)
- Role-based access control
- Invitation system
- Community-based filtering

---

## Prerequisites

### Backend Requirements
- ✅ Backend server running on `http://localhost:8000`
- ✅ Database seeded with admin account
- ✅ Admin credentials available

### iOS App Requirements
- ✅ Latest build with enterprise features
- ✅ API base URL configured to `http://localhost:8000`
- ✅ Device/simulator running iOS 15+

### Test Credentials

**Admin Account:**
- Email: `supportteam@artitecplatform.com`
- Password: `Password!`

---

## Test Scenarios

### Scenario 1: Perry Homes - Large Enterprise (10+ Communities)

**Business Context:**
Perry Homes operates in 10+ communities across the Houston area with multiple sales representatives per community.

**Expected Outcome:**
- Successfully provision Perry Homes as enterprise builder
- Assign sales reps to specific communities
- Verify access restrictions work correctly

### Scenario 2: Three-Tier Access Model

**Roles to Test:**
1. **Admin** - Full access to all communities and team management
2. **Manager** - Manage properties in assigned communities
3. **Sales Rep** - View/edit properties only in assigned communities
4. **Viewer** - Read-only access to assigned communities

---

## Part 1: Backend API Testing

### Test 1.1: Admin Login

**Endpoint:** `POST /v1/auth/login`

**Request:**
```bash
curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "supportteam@artitecplatform.com",
    "password": "Password!"
  }'
```

**Expected Response:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "public_id": "USR-...",
    "email": "supportteam@artitecplatform.com",
    "role": {
      "key": "admin",
      "name": "Admin"
    }
  }
}
```

**Verification:**
- ✅ Status code: 200
- ✅ Access token present
- ✅ User role is "admin"

**Save:** Copy the `access_token` for subsequent requests

---

### Test 1.2: Provision Enterprise Builder (Perry Homes)

**Endpoint:** `POST /v1/admin/enterprise/provision-builder`

**Request:**
```bash
curl -X POST http://localhost:8000/v1/admin/enterprise/provision-builder \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "company_name": "Perry Homes",
    "website_url": "https://www.perryhomes.com",
    "enterprise_number": "ENT-PERRY-2025",
    "company_address": "3000 Sage Rd, Houston, TX 77056",
    "staff_size": "500+",
    "years_in_business": 75,
    "primary_contact_email": "john.perry@perryhomes.test",
    "primary_contact_first_name": "John",
    "primary_contact_last_name": "Perry",
    "primary_contact_phone": "+17135551234",
    "invitation_expires_days": 14,
    "custom_message": "Welcome to Artitec! Perry Homes is now part of our enterprise builder program.",
    "plan_tier": "enterprise",
    "community_ids": []
  }'
```

**Expected Response:**
```json
{
  "builder": {
    "builder_id": "BLD-1234567890-XXXXX",
    "name": "Perry Homes",
    "website": "https://www.perryhomes.com",
    "verified": 1,
    "created_at": "2025-11-18T..."
  },
  "user": {
    "public_id": "USR-1234567890-XXXXX",
    "email": "john.perry@perryhomes.test",
    "first_name": "John",
    "last_name": "Perry"
  },
  "invitation": {
    "invitation_code": "X3P8Q1R9T2M4",
    "builder_id": "BLD-1234567890-XXXXX",
    "invited_email": "john.perry@perryhomes.test",
    "invited_role": "admin",
    "expires_at": "2025-12-02T...",
    "status": "pending"
  },
  "message": "Enterprise builder created successfully",
  "next_steps": [
    "Send invitation code to john.perry@perryhomes.test",
    "Primary contact should accept invitation to gain access",
    "Configure team members and community assignments"
  ]
}
```

**Verification:**
- ✅ Status code: 201
- ✅ Builder created with unique ID
- ✅ Admin user created
- ✅ 12-character invitation code generated
- ✅ Invitation expires in 14 days

**Save:**
- `builder_id`: For subsequent team management calls
- `invitation_code`: For testing invitation acceptance
- `user_id` (public_id): For team member updates

---

### Test 1.3: Validate Invitation

**Endpoint:** `GET /v1/admin/enterprise/invitations/{code}/validate`

**Request:**
```bash
curl -X GET "http://localhost:8000/v1/admin/enterprise/invitations/X3P8Q1R9T2M4/validate"
```

**Expected Response:**
```json
{
  "valid": true,
  "invitation_code": "X3P8Q1R9T2M4",
  "builder_name": "Perry Homes",
  "invited_email": "john.perry@perryhomes.test",
  "invited_role": "admin",
  "expires_at": "2025-12-02T...",
  "custom_message": "Welcome to Artitec! Perry Homes is now part of our enterprise builder program."
}
```

**Verification:**
- ✅ Status code: 200
- ✅ `valid`: true
- ✅ Builder name displayed correctly
- ✅ Custom message present

---

### Test 1.4: Accept Invitation

**Endpoint:** `POST /v1/admin/enterprise/invitations/accept`

**Setup:** First, register/login as the invited user

**Request:**
```bash
curl -X POST http://localhost:8000/v1/admin/enterprise/invitations/accept \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer USER_ACCESS_TOKEN" \
  -d '{
    "invitation_code": "X3P8Q1R9T2M4",
    "user_public_id": "USR-1234567890-XXXXX"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Invitation accepted successfully",
  "builder_id": "BLD-1234567890-XXXXX",
  "team_member_role": "admin"
}
```

**Verification:**
- ✅ Status code: 200
- ✅ User now has builder admin role
- ✅ Team member record created

---

### Test 1.5: List Team Members

**Endpoint:** `GET /v1/admin/builders/{builderId}/team-members`

**Request:**
```bash
curl -X GET "http://localhost:8000/v1/admin/builders/BLD-1234567890-XXXXX/team-members" \
  -H "Authorization: Bearer ADMIN_ACCESS_TOKEN"
```

**Expected Response:**
```json
{
  "builder_id": "BLD-1234567890-XXXXX",
  "builder_name": "Perry Homes",
  "team_members": [
    {
      "id": 1,
      "builder_id": "BLD-1234567890-XXXXX",
      "user_id": "USR-1234567890-XXXXX",
      "role": "admin",
      "permissions": null,
      "communities_assigned": null,
      "is_active": "active",
      "created_at": "2025-11-18T...",
      "user": {
        "public_id": "USR-1234567890-XXXXX",
        "first_name": "John",
        "last_name": "Perry",
        "email": "john.perry@perryhomes.test"
      }
    }
  ],
  "total_members": 1
}
```

**Verification:**
- ✅ Status code: 200
- ✅ Admin user listed
- ✅ `communities_assigned` is null (access to all)

---

### Test 1.6: Invite Team Member (Sales Rep)

**Endpoint:** `POST /v1/admin/builders/{builderId}/team-members/invite`

**Request:**
```bash
curl -X POST "http://localhost:8000/v1/admin/builders/BLD-1234567890-XXXXX/team-members/invite" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ADMIN_ACCESS_TOKEN" \
  -d '{
    "builder_id": "BLD-1234567890-XXXXX",
    "invited_email": "sarah.sales@perryhomes.test",
    "invited_role": "sales_rep",
    "invited_first_name": "Sarah",
    "invited_last_name": "Johnson",
    "invited_phone": "+17135554567",
    "communities_assigned": ["CMY-CINCO-RANCH", "CMY-BRIDGELAND"],
    "custom_message": "Welcome to the Perry Homes sales team!",
    "invitation_expires_days": 7
  }'
```

**Expected Response:**
```json
{
  "invitation": {
    "invitation_code": "Y4Q9R2T3M5N6",
    "builder_id": "BLD-1234567890-XXXXX",
    "invited_email": "sarah.sales@perryhomes.test",
    "invited_role": "sales_rep",
    "invited_first_name": "Sarah",
    "invited_last_name": "Johnson",
    "expires_at": "2025-11-25T...",
    "status": "pending"
  },
  "message": "Team member invitation sent successfully"
}
```

**Verification:**
- ✅ Status code: 201
- ✅ New invitation code generated
- ✅ Role is "sales_rep"
- ✅ Expires in 7 days

**Save:** `invitation_code` for sales rep acceptance test

---

### Test 1.7: Update Team Member

**Endpoint:** `PUT /v1/admin/builders/{builderId}/team-members/{userId}`

**Request:**
```bash
curl -X PUT "http://localhost:8000/v1/admin/builders/BLD-1234567890-XXXXX/team-members/USR-1234567890-XXXXX" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ADMIN_ACCESS_TOKEN" \
  -d '{
    "role": "manager",
    "communities_assigned": ["CMY-CINCO-RANCH", "CMY-BRIDGELAND", "CMY-WOODLANDS"],
    "is_active": "active"
  }'
```

**Expected Response:**
```json
{
  "id": 1,
  "builder_id": "BLD-1234567890-XXXXX",
  "user_id": "USR-1234567890-XXXXX",
  "role": "manager",
  "communities_assigned": ["CMY-CINCO-RANCH", "CMY-BRIDGELAND", "CMY-WOODLANDS"],
  "is_active": "active",
  "user": {
    "public_id": "USR-1234567890-XXXXX",
    "first_name": "John",
    "last_name": "Perry",
    "email": "john.perry@perryhomes.test"
  }
}
```

**Verification:**
- ✅ Status code: 200
- ✅ Role changed to "manager"
- ✅ Communities assigned correctly
- ✅ Still active

---

### Test 1.8: List Builder Communities

**Endpoint:** `GET /v1/admin/builders/{builderId}/communities`

**Request:**
```bash
curl -X GET "http://localhost:8000/v1/admin/builders/BLD-1234567890-XXXXX/communities" \
  -H "Authorization: Bearer ADMIN_ACCESS_TOKEN"
```

**Expected Response:**
```json
{
  "builder_id": "BLD-1234567890-XXXXX",
  "builder_name": "Perry Homes",
  "communities": [
    {
      "community_id": "CMY-CINCO-RANCH",
      "name": "Cinco Ranch",
      "city": "Katy",
      "state": "TX",
      "property_count": 25,
      "active_status": "active"
    },
    {
      "community_id": "CMY-BRIDGELAND",
      "name": "Bridgeland",
      "city": "Cypress",
      "state": "TX",
      "property_count": 18,
      "active_status": "active"
    }
  ],
  "total_communities": 2
}
```

**Verification:**
- ✅ Status code: 200
- ✅ Communities listed correctly
- ✅ Property counts are builder-specific

---

## Part 2: iOS App Testing

### Test 2.1: Admin Provisioning Flow

**Prerequisites:**
- iOS app running
- Logged in as admin (`supportteam@artitecplatform.com`)

**Steps:**
1. Navigate to Admin Panel
2. Tap **"Provision Enterprise Builder"**
3. Fill in company information:
   - Company Name: **Perry Homes**
   - Website: **https://www.perryhomes.com**
   - Enterprise Number: **ENT-PERRY-2025**
   - Address: **3000 Sage Rd, Houston, TX 77056**
   - Staff Size: **500+**
   - Years in Business: **75**
4. Fill in primary contact:
   - First Name: **John**
   - Last Name: **Perry**
   - Email: **john.perry@perryhomes.test**
   - Phone: **+17135551234**
5. (Optional) Tap **"Select Communities"** to assign communities
6. Tap **"Create Enterprise Builder Account"**

**Expected Results:**
- ✅ Success alert appears
- ✅ Invitation code displayed (12 characters)
- ✅ Option to copy invitation code
- ✅ "Next Steps" information shown

**Save:** Copy the invitation code for next test

---

### Test 2.2: Invitation Acceptance Flow

**Prerequisites:**
- Invitation code from Test 2.1
- Registered user account

**Steps:**
1. Logout from admin account
2. Register/Login with invited email (`john.perry@perryhomes.test`)
3. Navigate to **"Join Builder Team"** or **"Enterprise Invitation"**
4. Enter invitation code: **[CODE FROM TEST 2.1]**
5. Tap **"Validate Invitation"**

**Expected Results:**
- ✅ Validation success
- ✅ Builder name displayed: **Perry Homes**
- ✅ Email displayed: **john.perry@perryhomes.test**
- ✅ Role displayed: **Administrator**
- ✅ Custom message shown

**Continue:**
6. Review invitation details
7. Tap **"Accept Invitation"**

**Expected Results:**
- ✅ Success alert: "You've successfully joined the builder's team!"
- ✅ User role updated to builder admin
- ✅ Access to team management features

---

### Test 2.3: Team Management View

**Prerequisites:**
- Logged in as builder admin

**Steps:**
1. Navigate to **"Team Management"**

**Expected Results:**
- ✅ Team summary badges shown:
  - Total Members: **1**
  - Communities: **[count]**
- ✅ Admin section shows John Perry
- ✅ Floating action button **"+ Invite Team Member"** visible

---

### Test 2.4: Invite Team Member (Sales Rep)

**Prerequisites:**
- In Team Management view
- Logged in as builder admin

**Steps:**
1. Tap **"+ Invite Team Member"**
2. Fill in team member information:
   - First Name: **Sarah**
   - Last Name: **Johnson**
   - Email: **sarah.sales@perryhomes.test**
   - Phone: **+17135554567**
3. Select role: **Sales Representative**
4. Configure community access:
   - Uncheck **"Access to All Communities"**
   - Select **Cinco Ranch**
   - Select **Bridgeland**
5. (Optional) Enter custom message
6. Tap **"Send Invitation"**

**Expected Results:**
- ✅ Success alert appears
- ✅ Invitation code can be copied
- ✅ Team list refreshes
- ✅ New pending invitation visible

**Save:** Copy invitation code for sales rep

---

### Test 2.5: Edit Team Member

**Prerequisites:**
- At least one team member exists
- In Team Management view

**Steps:**
1. Tap on team member **"John Perry"**
2. Change role to: **Manager**
3. Update community access:
   - Add **The Woodlands** community
4. Tap **"Save"**

**Expected Results:**
- ✅ Success message
- ✅ Team member role updated in list
- ✅ Community count updated
- ✅ Changes persist after refresh

---

### Test 2.6: Community-Based Access (Sales Rep View)

**Prerequisites:**
- Sales rep invitation accepted
- Logged in as sales rep (`sarah.sales@perryhomes.test`)

**Steps:**
1. Navigate to **"Communities"** tab

**Expected Results:**
- ✅ Only assigned communities visible:
  - Cinco Ranch ✅
  - Bridgeland ✅
  - Other communities NOT visible ❌

2. Navigate to **"Properties"** tab

**Expected Results:**
- ✅ Only properties in assigned communities visible
- ✅ Properties in unassigned communities NOT visible
- ✅ Cannot create properties in unassigned communities

---

### Test 2.7: Role-Based Access Control

**Test Matrix:**

| Feature | Admin | Manager | Sales Rep | Viewer |
|---------|-------|---------|-----------|--------|
| View all communities | ✅ | ✅ (assigned) | ✅ (assigned) | ✅ (assigned) |
| Manage team members | ✅ | ❌ | ❌ | ❌ |
| Create properties | ✅ | ✅ (assigned) | ✅ (assigned) | ❌ |
| Edit properties | ✅ | ✅ (assigned) | ✅ (assigned) | ❌ |
| View reports | ✅ | ✅ | ❌ | ❌ |
| Invite team members | ✅ | ❌ | ❌ | ❌ |

**Test Steps for Each Role:**
1. Login as role user
2. Verify accessible features match table
3. Attempt restricted actions (should fail gracefully)

---

## Part 3: Edge Cases & Error Handling

### Test 3.1: Invalid Invitation Code

**Steps:**
1. Enter invitation code: `INVALIDCODE`
2. Tap **"Validate Invitation"**

**Expected:**
- ✅ Error alert: "Invalid invitation code"
- ✅ No crash

---

### Test 3.2: Expired Invitation

**Steps:**
1. Use invitation code created 15+ days ago
2. Attempt to validate

**Expected:**
- ✅ Error: "Invitation has expired"
- ✅ Suggestion to request new invitation

---

### Test 3.3: Duplicate Email Invitation

**Steps:**
1. Invite team member with email already invited
2. Attempt to send invitation

**Expected:**
- ✅ Error: "User already invited or is a team member"
- ✅ Clear error message

---

### Test 3.4: Remove Community Assignment

**Steps:**
1. Edit team member with community assignments
2. Change to "Access to All Communities"
3. Save

**Expected:**
- ✅ `communities_assigned` becomes null
- ✅ User can now access all communities
- ✅ UI reflects change

---

### Test 3.5: Deactivate Team Member

**Steps:**
1. Edit active team member
2. Toggle **"Active"** to OFF
3. Save

**Expected:**
- ✅ Member status: "Inactive"
- ✅ Member cannot login to builder account
- ✅ Can be reactivated later

---

## Part 4: Multi-Community Scenarios

### Test 4.1: Perry Homes (10+ Communities)

**Setup:**
Create builder with 10 Houston-area communities:
- Cinco Ranch (Katy, TX)
- Bridgeland (Cypress, TX)
- The Woodlands (The Woodlands, TX)
- Sienna (Missouri City, TX)
- Cross Creek Ranch (Fulshear, TX)
- Grand Lakes (Katy, TX)
- Riverstone (Sugar Land, TX)
- Meridiana (Iowa Colony, TX)
- Jordan Ranch (Fulshear, TX)
- Alta Vista (Pearland, TX)

**Team Structure:**
- **1 Admin** - Full access
- **2 Managers** - 5 communities each (regional)
- **10 Sales Reps** - 1-2 communities each
- **2 Viewers** - All communities (marketing team)

**Test:**
1. Provision builder
2. Invite all team members
3. Verify access restrictions work correctly
4. Test property creation in assigned vs unassigned communities

---

### Test 4.2: Community Reassignment

**Scenario:** Sales rep moves from Cinco Ranch to The Woodlands

**Steps:**
1. Edit sales rep
2. Remove Cinco Ranch from assignments
3. Add The Woodlands
4. Save

**Expected:**
- ✅ Sales rep loses access to Cinco Ranch properties
- ✅ Sales rep gains access to Woodlands properties
- ✅ Existing work saved correctly

---

## Part 5: Performance Testing

### Test 5.1: Large Team (50+ Members)

**Steps:**
1. Create builder
2. Invite 50 team members
3. Load team management view

**Expected:**
- ✅ List loads within 2 seconds
- ✅ Smooth scrolling
- ✅ Search/filter works correctly

---

### Test 5.2: Concurrent Invitations

**Steps:**
1. Send 5 invitations simultaneously
2. Verify all created correctly

**Expected:**
- ✅ All invitations successful
- ✅ Unique invitation codes
- ✅ No duplicates

---

## Troubleshooting

### Issue: "Cannot connect to server"

**Solution:**
1. Verify backend is running: `curl http://localhost:8000/`
2. Check iOS app API base URL setting
3. Ensure device/simulator can reach localhost

### Issue: "Unauthorized" errors

**Solution:**
1. Verify access token is valid
2. Re-login if token expired
3. Check user has required permissions

### Issue: "Community not found"

**Solution:**
1. Verify community IDs are correct
2. Check builder-community associations
3. Ensure communities exist in database

### Issue: Invitation code not working

**Solution:**
1. Check invitation hasn't expired
2. Verify code entered correctly (case-sensitive)
3. Ensure invitation status is "pending"

---

## API Reference Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/admin/enterprise/provision-builder` | POST | Provision enterprise builder |
| `/v1/admin/enterprise/invitations/{code}/validate` | GET | Validate invitation code |
| `/v1/admin/enterprise/invitations/accept` | POST | Accept invitation |
| `/v1/admin/builders/{builderId}/team-members` | GET | List team members |
| `/v1/admin/builders/{builderId}/team-members/invite` | POST | Invite team member |
| `/v1/admin/builders/{builderId}/team-members/{userId}` | PUT | Update team member |
| `/v1/admin/builders/{builderId}/communities` | GET | List builder communities |

---

## Test Completion Checklist

### Phase 1: Provisioning
- [ ] Admin can login
- [ ] Enterprise builder provisioned successfully
- [ ] Invitation code generated
- [ ] Invitation can be validated
- [ ] Invitation can be accepted
- [ ] Builder admin has correct role

### Phase 2: Team Management
- [ ] Team members list displays correctly
- [ ] Can invite new team members
- [ ] Community assignments work
- [ ] Role changes applied correctly
- [ ] Active/inactive status toggles
- [ ] Remove team member works

### Phase 3: Access Control
- [ ] Admins see all communities
- [ ] Sales reps see only assigned communities
- [ ] Property access restricted correctly
- [ ] Team management restricted to admins
- [ ] Viewers have read-only access

### Phase 4: iOS App
- [ ] Provisioning UI works
- [ ] Invitation acceptance flow works
- [ ] Team management view loads
- [ ] Invite UI functional
- [ ] Edit UI functional
- [ ] Community filtering works

---

## Success Criteria

**All tests passing means:**
- ✅ Enterprise builders can be provisioned
- ✅ Multi-community assignments work correctly
- ✅ Role-based access control enforced
- ✅ Invitation system functional
- ✅ iOS UI operational
- ✅ Backend APIs responding correctly

---

## Next Steps After Testing

1. **Document issues** found during testing
2. **Gather user feedback** on UX/UI
3. **Performance optimization** if needed
4. **Add remaining features:**
   - Community-based property filtering
   - Advanced permissions
   - Bulk operations
5. **Prepare for production** deployment

---

## Support

For issues or questions:
- Check backend logs: `/Users/adeniyi_family_executor/Documents/Development/Artitec Backend Development/logs/`
- Review API documentation
- Contact development team

---

**Document Version:** 1.0
**Last Updated:** November 18, 2025
**Status:** Phase 2 Complete - Ready for Testing
