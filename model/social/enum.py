# social/enums.py
from enum import StrEnum
class TargetType(StrEnum):
    builder = "builder"
    community = "community"
    user = "user"
    post = "post"
    comment = "comment"
    property = "property"