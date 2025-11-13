# routes/followers.py
"""
API endpoints for follow/unfollow functionality.
Enables users to follow other users and view follower/following lists.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from model.followers import Follower
from model.profiles.buyer import BuyerProfile
from deps import get_db, require_auth

router = APIRouter(prefix="/v1/followers", tags=["followers"])


# ============================================================================
# Pydantic Schemas
# ============================================================================

class FollowRequest(BaseModel):
    """Request to follow a user."""
    following_user_id: int  # ID of user to follow


class FollowResponse(BaseModel):
    """Response after follow/unfollow action."""
    success: bool
    message: str
    followers_count: int  # Updated follower count for the target user


class FollowerOut(BaseModel):
    """Follower/Following user info."""
    user_id: str
    public_id: str
    display_name: Optional[str] = None
    profile_image: Optional[str] = None
    followed_at: datetime

    class Config:
        from_attributes = True


class FollowStatsOut(BaseModel):
    """Follow statistics for a user."""
    user_id: str
    followers_count: int
    following_count: int
    is_following: bool  # Whether the current user follows this user


# ============================================================================
# Helper Functions
# ============================================================================

async def update_followers_count(db: AsyncSession, user_id: str) -> int:
    """
    Update and return the followers count for a user.
    This updates the denormalized counter in buyer_profiles.
    """
    # Count followers
    result = await db.execute(
        select(func.count(Follower.id)).where(Follower.following_user_id == user_id)
    )
    count = result.scalar() or 0

    # Update buyer_profiles if exists
    buyer = await db.execute(
        select(BuyerProfile).where(BuyerProfile.user_id == user_id)
    )
    buyer_profile = buyer.scalar_one_or_none()

    if buyer_profile:
        buyer_profile.followers_count = count
        await db.commit()

    return count


# ============================================================================
# Follow/Unfollow Endpoints
# ============================================================================

@router.post("/{user_id}/follow", response_model=FollowResponse)
async def follow_user(
    user_id: str,
    current_user=Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Follow a user.

    - **user_id**: ID of user to follow (user_id string like USR-xxx)
    - Returns success status and updated follower count
    """
    follower_id = current_user.user_id

    # Cannot follow yourself
    if follower_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot follow yourself"
        )

    # Check if already following
    existing = await db.execute(
        select(Follower).where(
            and_(
                Follower.follower_user_id == follower_id,
                Follower.following_user_id == user_id
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already following this user"
        )

    # Create follow relationship
    follow = Follower(
        follower_user_id=follower_id,
        following_user_id=user_id
    )
    db.add(follow)
    await db.commit()

    # Update followers count
    new_count = await update_followers_count(db, user_id)

    return FollowResponse(
        success=True,
        message="Successfully followed user",
        followers_count=new_count
    )


@router.delete("/{user_id}/follow", response_model=FollowResponse)
async def unfollow_user(
    user_id: str,
    current_user=Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Unfollow a user.

    - **user_id**: ID of user to unfollow (user_id string like USR-xxx)
    - Returns success status and updated follower count
    """
    follower_id = current_user.user_id

    # Find and delete follow relationship
    result = await db.execute(
        select(Follower).where(
            and_(
                Follower.follower_user_id == follower_id,
                Follower.following_user_id == user_id
            )
        )
    )
    follow = result.scalar_one_or_none()

    if not follow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not following this user"
        )

    await db.delete(follow)
    await db.commit()

    # Update followers count
    new_count = await update_followers_count(db, user_id)

    return FollowResponse(
        success=True,
        message="Successfully unfollowed user",
        followers_count=new_count
    )


# ============================================================================
# Query Endpoints
# ============================================================================

@router.get("/{user_id}/followers", response_model=List[FollowerOut])
async def get_followers(
    user_id: str,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of users following the specified user.

    - **user_id**: User whose followers to retrieve (user_id string like USR-xxx)
    - **skip**: Pagination offset
    - **limit**: Maximum results (max 100)
    """
    if limit > 100:
        limit = 100

    # Query followers with user info
    query = (
        select(Follower, BuyerProfile)
        .join(BuyerProfile, BuyerProfile.user_id == Follower.follower_user_id, isouter=True)
        .where(Follower.following_user_id == user_id)
        .order_by(Follower.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(query)
    rows = result.all()

    followers = []
    for follow, profile in rows:
        followers.append(FollowerOut(
            user_id=follow.follower_user_id,
            public_id=follow.follower_user_id,  # Now this is the actual user_id string
            display_name=profile.display_name if profile else None,
            profile_image=profile.profile_image if profile else None,
            followed_at=follow.created_at
        ))

    return followers


@router.get("/{user_id}/following", response_model=List[FollowerOut])
async def get_following(
    user_id: str,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of users that the specified user is following.

    - **user_id**: User whose following list to retrieve (user_id string like USR-xxx)
    - **skip**: Pagination offset
    - **limit**: Maximum results (max 100)
    """
    if limit > 100:
        limit = 100

    # Query following with user info
    query = (
        select(Follower, BuyerProfile)
        .join(BuyerProfile, BuyerProfile.user_id == Follower.following_user_id, isouter=True)
        .where(Follower.follower_user_id == user_id)
        .order_by(Follower.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(query)
    rows = result.all()

    following = []
    for follow, profile in rows:
        following.append(FollowerOut(
            user_id=follow.following_user_id,
            public_id=follow.following_user_id,  # Now this is the actual user_id string
            display_name=profile.display_name if profile else None,
            profile_image=profile.profile_image if profile else None,
            followed_at=follow.created_at
        ))

    return following


@router.get("/{user_id}/stats", response_model=FollowStatsOut)
async def get_follow_stats(
    user_id: str,
    current_user=Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Get follow statistics for a user.

    - **user_id**: User whose stats to retrieve (user_id string like USR-xxx)
    - Returns follower count, following count, and whether current user follows them
    """
    # Count followers
    followers_result = await db.execute(
        select(func.count(Follower.id)).where(Follower.following_user_id == user_id)
    )
    followers_count = followers_result.scalar() or 0

    # Count following
    following_result = await db.execute(
        select(func.count(Follower.id)).where(Follower.follower_user_id == user_id)
    )
    following_count = following_result.scalar() or 0

    # Check if current user follows this user
    is_following_result = await db.execute(
        select(Follower).where(
            and_(
                Follower.follower_user_id == current_user.user_id,
                Follower.following_user_id == user_id
            )
        )
    )
    is_following = is_following_result.scalar_one_or_none() is not None

    return FollowStatsOut(
        user_id=user_id,
        followers_count=followers_count,
        following_count=following_count,
        is_following=is_following
    )
