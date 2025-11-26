"""
Duplicate Detection Utilities

Provides fuzzy matching and duplicate detection for entities to prevent
duplicate communities and builders from being created.
"""
import logging
from typing import Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


def calculate_similarity(str1: str, str2: str) -> float:
    """
    Calculate similarity ratio between two strings.

    Returns:
        float: Similarity score from 0.0 to 1.0
    """
    if not str1 or not str2:
        return 0.0

    # Normalize strings
    s1 = str1.lower().strip()
    s2 = str2.lower().strip()

    return SequenceMatcher(None, s1, s2).ratio()


def find_duplicate_community(
    db: Session,
    name: str,
    city: Optional[str] = None,
    state: Optional[str] = None,
    website: Optional[str] = None,
    address: Optional[str] = None,
    threshold: float = 0.85
) -> Tuple[Optional[int], Optional[float], Optional[str]]:
    """
    Search for duplicate community in database.

    Matching criteria (in priority order):
    1. Exact website URL match (confidence: 1.0)
    2. Exact name + city + state match (confidence: 0.95)
    3. Fuzzy name match + location match (confidence: varies)
    4. Address similarity (confidence: varies)

    Args:
        db: Database session
        name: Community name
        city: City name
        state: State code
        website: Website URL
        address: Physical address
        threshold: Minimum similarity score (0.0-1.0)

    Returns:
        Tuple of (entity_id, confidence_score, match_method) or (None, None, None)
    """
    from model.profiles.community import Community

    # Method 1: Exact website match (highest confidence)
    if website:
        normalized_website = website.lower().strip().rstrip('/')
        existing = db.query(Community).filter(
            func.lower(Community.community_website_url) == normalized_website
        ).first()

        if existing:
            logger.info(f"Found exact website match for {name}: {existing.name} (ID: {existing.id})")
            return existing.id, 1.0, "website_exact"

    # Method 2: Exact name + location match
    if city and state:
        existing = db.query(Community).filter(
            func.lower(Community.name) == name.lower().strip(),
            func.lower(Community.city) == city.lower().strip(),
            func.lower(Community.state) == state.upper().strip()
        ).first()

        if existing:
            logger.info(f"Found exact name+location match for {name}: {existing.name} (ID: {existing.id})")
            return existing.id, 0.95, "name_location_exact"

    # Method 3: Fuzzy name matching with location
    if city or state:
        # Get all communities in the same city or state
        query = db.query(Community)

        if city and state:
            query = query.filter(
                or_(
                    func.lower(Community.city) == city.lower().strip(),
                    func.lower(Community.state) == state.upper().strip()
                )
            )
        elif city:
            query = query.filter(func.lower(Community.city) == city.lower().strip())
        elif state:
            query = query.filter(func.lower(Community.state) == state.upper().strip())

        candidates = query.all()

        best_match = None
        best_score = 0.0

        for candidate in candidates:
            name_similarity = calculate_similarity(name, candidate.name)

            # Boost score if location matches perfectly
            location_boost = 0.0
            if city and candidate.city and city.lower() == candidate.city.lower():
                location_boost += 0.05
            if state and candidate.state and state.upper() == candidate.state.upper():
                location_boost += 0.05

            total_score = min(name_similarity + location_boost, 1.0)

            if total_score > best_score and total_score >= threshold:
                best_score = total_score
                best_match = candidate

        if best_match:
            logger.info(f"Found fuzzy match for {name}: {best_match.name} (ID: {best_match.id}, score: {best_score:.2f})")
            return best_match.id, best_score, "name_fuzzy"

    # Method 4: Address matching (if no location provided)
    if address and not (city or state):
        existing = db.query(Community).filter(
            Community.address.isnot(None)
        ).all()

        best_match = None
        best_score = 0.0

        for candidate in existing:
            if candidate.address:
                addr_similarity = calculate_similarity(address, candidate.address)

                if addr_similarity > best_score and addr_similarity >= threshold:
                    best_score = addr_similarity
                    best_match = candidate

        if best_match:
            logger.info(f"Found address match for {name}: {best_match.name} (ID: {best_match.id}, score: {best_score:.2f})")
            return best_match.id, best_score, "address_fuzzy"

    logger.info(f"No duplicate found for community: {name}")
    return None, None, None


def find_duplicate_builder(
    db: Session,
    name: str,
    city: Optional[str] = None,
    state: Optional[str] = None,
    website: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    threshold: float = 0.85
) -> Tuple[Optional[int], Optional[float], Optional[str]]:
    """
    Search for duplicate builder in database.

    Matching criteria (in priority order):
    1. Exact website URL match (confidence: 1.0)
    2. Exact email match (confidence: 0.98)
    3. Exact phone match (confidence: 0.95)
    4. Exact name + location match (confidence: 0.93)
    5. Fuzzy name match + location (confidence: varies)

    Args:
        db: Database session
        name: Builder name
        city: City name
        state: State code
        website: Website URL
        phone: Phone number
        email: Email address
        threshold: Minimum similarity score (0.0-1.0)

    Returns:
        Tuple of (entity_id, confidence_score, match_method) or (None, None, None)
    """
    from model.profiles.builder import BuilderProfile

    # Method 1: Exact website match (highest confidence)
    if website:
        normalized_website = website.lower().strip().rstrip('/')
        existing = db.query(BuilderProfile).filter(
            func.lower(BuilderProfile.website) == normalized_website
        ).first()

        if existing:
            logger.info(f"Found exact website match for builder {name}: {existing.name} (ID: {existing.id})")
            return existing.id, 1.0, "website_exact"

    # Method 2: Exact email match
    if email:
        normalized_email = email.lower().strip()
        existing = db.query(BuilderProfile).filter(
            func.lower(BuilderProfile.email) == normalized_email
        ).first()

        if existing:
            logger.info(f"Found exact email match for builder {name}: {existing.name} (ID: {existing.id})")
            return existing.id, 0.98, "email_exact"

    # Method 3: Exact phone match
    if phone:
        # Normalize phone number (remove spaces, dashes, parentheses)
        normalized_phone = ''.join(c for c in phone if c.isdigit())

        all_builders = db.query(BuilderProfile).filter(
            BuilderProfile.phone.isnot(None)
        ).all()

        for builder in all_builders:
            if builder.phone:
                builder_phone = ''.join(c for c in builder.phone if c.isdigit())
                if normalized_phone == builder_phone:
                    logger.info(f"Found exact phone match for builder {name}: {builder.name} (ID: {builder.id})")
                    return builder.id, 0.95, "phone_exact"

    # Method 4: Exact name + location match
    if city and state:
        existing = db.query(BuilderProfile).filter(
            func.lower(BuilderProfile.name) == name.lower().strip(),
            func.lower(BuilderProfile.city) == city.lower().strip(),
            func.lower(BuilderProfile.state) == state.upper().strip()
        ).first()

        if existing:
            logger.info(f"Found exact name+location match for builder {name}: {existing.name} (ID: {existing.id})")
            return existing.id, 0.93, "name_location_exact"

    # Method 5: Fuzzy name matching with location
    if city or state:
        query = db.query(BuilderProfile)

        if city and state:
            query = query.filter(
                or_(
                    func.lower(BuilderProfile.city) == city.lower().strip(),
                    func.lower(BuilderProfile.state) == state.upper().strip()
                )
            )
        elif city:
            query = query.filter(func.lower(BuilderProfile.city) == city.lower().strip())
        elif state:
            query = query.filter(func.lower(BuilderProfile.state) == state.upper().strip())

        candidates = query.all()

        best_match = None
        best_score = 0.0

        for candidate in candidates:
            name_similarity = calculate_similarity(name, candidate.name)

            # Boost score if location matches perfectly
            location_boost = 0.0
            if city and candidate.city and city.lower() == candidate.city.lower():
                location_boost += 0.05
            if state and candidate.state and state.upper() == candidate.state.upper():
                location_boost += 0.05

            total_score = min(name_similarity + location_boost, 1.0)

            if total_score > best_score and total_score >= threshold:
                best_score = total_score
                best_match = candidate

        if best_match:
            logger.info(f"Found fuzzy match for builder {name}: {best_match.name} (ID: {best_match.id}, score: {best_score:.2f})")
            return best_match.id, best_score, "name_fuzzy"

    logger.info(f"No duplicate found for builder: {name}")
    return None, None, None
