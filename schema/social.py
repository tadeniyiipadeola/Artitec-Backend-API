from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, conint


# ------------------------------------------------------------
# Common request body for follow/like toggles
# ------------------------------------------------------------
class SocialToggle(BaseModel):
    target_type: Literal["builder", "community", "user", "post", "comment", "property"]
    target_id: conint(ge=1)


# ------------------------------------------------------------
# Comments
# ------------------------------------------------------------
class CommentCreate(BaseModel):
    target_type: Literal["builder", "community", "user", "post", "comment", "property"]
    target_id: conint(ge=1)
    parent_id: Optional[int] = None
    body: str = Field(min_length=1, max_length=5000)


class CommentOut(BaseModel):
    id: int
    author_id: int
    body: str
    parent_id: Optional[int] = None
    created_at: datetime
    is_deleted: bool = False
    like_count: int = 0
    is_liked: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


__all__ = [
    "SocialToggle",
    "CommentCreate",
    "CommentOut",
]