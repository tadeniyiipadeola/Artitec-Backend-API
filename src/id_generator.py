# src/id_generator.py
"""
Typed Public ID Generator for Artitec
Generates IDs in format: PREFIX-TIMESTAMP-RANDOM
Example: USR-1699564234-A7K9M2
"""

import secrets
import time


# Prefix mapping for all resource types
PREFIX_MAP = {
    "user": "USR",
    "buyer": "BYR",
    "builder": "BLD",
    "community": "CMY",
    "community_admin": "ADM",
    "sales_rep": "SLS",
    "property": "PRP",
    "tour": "TUR",
    "document": "DOC",
    "event": "EVT",
    "message": "MSG",
    "notification": "NTF",
    "media": "MED",
}


def generate_public_id(prefix: str) -> str:
    """
    Generate a typed public ID with format: PREFIX-TIMESTAMP-RANDOM

    Args:
        prefix: 3-letter type prefix (e.g., "USR", "BYR", "BLD") or resource type name (e.g., "user", "media")

    Returns:
        str: Public ID in format PREFIX-TIMESTAMP-RANDOM
        Example: "USR-1699564234-A7K9M2"

    Security notes:
        - Timestamp provides chronological sortability
        - Random component prevents enumeration attacks
        - 6-char alphanumeric = 36^6 = ~2 billion combinations per second
        - Collision probability is negligible in practice
    """
    # If prefix is a resource type name, look it up in PREFIX_MAP
    if prefix in PREFIX_MAP:
        prefix = PREFIX_MAP[prefix]

    timestamp = int(time.time())

    # Generate 6-character random alphanumeric string (uppercase)
    # Uses secrets module for cryptographically strong randomness
    random_bytes = secrets.token_urlsafe(6)
    random_part = random_bytes.replace('-', '').replace('_', '')[:6].upper()

    return f"{prefix}-{timestamp}-{random_part}"


def generate_user_id() -> str:
    """Generate a user public ID: USR-1699564234-A7K9M2"""
    return generate_public_id(PREFIX_MAP["user"])


def generate_buyer_id() -> str:
    """Generate a buyer profile public ID: BYR-1699564234-A7K9M2"""
    return generate_public_id(PREFIX_MAP["buyer"])


def generate_builder_id() -> str:
    """Generate a builder profile public ID: BLD-1699564234-X3P8Q1"""
    return generate_public_id(PREFIX_MAP["builder"])


def generate_community_id() -> str:
    """Generate a community public ID: CMY-1699564234-Z5R7N4"""
    return generate_public_id(PREFIX_MAP["community"])


def generate_community_admin_id() -> str:
    """Generate a community admin profile public ID: ADM-1699564234-M2K9L3"""
    return generate_public_id(PREFIX_MAP["community_admin"])


def generate_sales_rep_id() -> str:
    """Generate a sales rep profile public ID: SLS-1699564234-P7Q8R9"""
    return generate_public_id(PREFIX_MAP["sales_rep"])


def generate_property_id() -> str:
    """Generate a property public ID: PRP-1699564234-S1T2U3"""
    return generate_public_id(PREFIX_MAP["property"])


def parse_public_id(public_id: str) -> dict:
    """
    Parse a public ID into its components.

    Args:
        public_id: Public ID string (e.g., "USR-1699564234-A7K9M2")

    Returns:
        dict with keys: prefix, timestamp, random, resource_type

    Example:
        >>> parse_public_id("USR-1699564234-A7K9M2")
        {
            "prefix": "USR",
            "timestamp": 1699564234,
            "random": "A7K9M2",
            "resource_type": "user"
        }
    """
    try:
        parts = public_id.split("-")
        if len(parts) != 3:
            raise ValueError(f"Invalid public ID format: {public_id}")

        prefix, timestamp_str, random_part = parts

        # Reverse lookup resource type from prefix
        resource_type = None
        for rtype, rpref in PREFIX_MAP.items():
            if rpref == prefix:
                resource_type = rtype
                break

        return {
            "prefix": prefix,
            "timestamp": int(timestamp_str),
            "random": random_part,
            "resource_type": resource_type,
        }
    except (ValueError, IndexError) as e:
        raise ValueError(f"Failed to parse public ID '{public_id}': {e}")


def validate_public_id(public_id: str, expected_prefix: str = None) -> bool:
    """
    Validate a public ID format and optionally check the prefix.

    Args:
        public_id: Public ID to validate
        expected_prefix: Optional prefix to check (e.g., "USR", "BYR")

    Returns:
        bool: True if valid, False otherwise

    Example:
        >>> validate_public_id("USR-1699564234-A7K9M2", "USR")
        True
        >>> validate_public_id("BYR-1699564234-A7K9M2", "USR")
        False
    """
    try:
        parsed = parse_public_id(public_id)

        # Check prefix if specified
        if expected_prefix and parsed["prefix"] != expected_prefix:
            return False

        # Validate components
        if not parsed["prefix"].isupper():
            return False
        if not parsed["random"].isalnum():
            return False
        if len(parsed["random"]) != 6:
            return False

        return True
    except (ValueError, KeyError):
        return False


# Export public functions
__all__ = [
    "PREFIX_MAP",
    "generate_public_id",
    "generate_user_id",
    "generate_buyer_id",
    "generate_builder_id",
    "generate_community_id",
    "generate_community_admin_id",
    "generate_sales_rep_id",
    "generate_property_id",
    "parse_public_id",
    "validate_public_id",
]
