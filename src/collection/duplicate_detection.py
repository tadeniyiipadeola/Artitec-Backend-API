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


def validate_builder_location(
    db: Session,
    builder: 'BuilderProfile',
    community_id: Optional[int] = None,
    city: Optional[str] = None,
    state: Optional[str] = None
) -> bool:
    """
    Validate that a builder serves the specified location.

    Checks:
    1. Builder is linked to the specific community (via builder_communities relationship)
    2. Builder's service_areas include the city/state
    3. Builder has the same city/state as the collection location

    Args:
        db: Database session
        builder: BuilderProfile to validate
        community_id: Community ID from collection context
        city: City from collection
        state: State from collection

    Returns:
        bool: True if builder serves this location, False otherwise
    """
    # Check 1: Direct community linkage (highest confidence)
    if community_id:
        # Check if builder is linked to this community via many-to-many relationship
        from model.profiles.builder import builder_communities
        from sqlalchemy import select

        community_link = db.execute(
            select(builder_communities).where(
                builder_communities.c.builder_id == builder.id,
                builder_communities.c.community_id == community_id
            )
        ).first()

        if community_link:
            logger.info(f"Builder {builder.name} (ID: {builder.id}) is linked to community ID {community_id}")
            return True

    # Check 2: Service areas match
    if builder.service_areas and isinstance(builder.service_areas, list):
        if city or state:
            for service_area in builder.service_areas:
                if isinstance(service_area, str):
                    service_area_lower = service_area.lower()
                    if city and city.lower() in service_area_lower:
                        logger.info(f"Builder {builder.name} service area includes city: {city}")
                        return True
                    if state and state.upper() in service_area.upper():
                        logger.info(f"Builder {builder.name} service area includes state: {state}")
                        return True
                elif isinstance(service_area, dict):
                    # Handle structured service area data
                    if city and service_area.get('city', '').lower() == city.lower():
                        return True
                    if state and service_area.get('state', '').upper() == state.upper():
                        return True

    # Check 3: Builder's stored location matches collection location
    location_match = False
    if city and builder.city and city.lower().strip() == builder.city.lower().strip():
        location_match = True
    if state and builder.state and state.upper().strip() == builder.state.upper().strip():
        location_match = True

    if location_match:
        logger.info(f"Builder {builder.name} location ({builder.city}, {builder.state}) matches collection location ({city}, {state})")
        return True

    logger.info(f"Builder {builder.name} location validation failed for community {community_id}, {city}, {state}")
    return False


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
    if name and city and state:
        existing = db.query(Community).filter(
            func.lower(Community.name) == name.lower().strip(),
            func.lower(Community.city) == city.lower().strip(),
            func.lower(Community.state) == state.upper().strip()
        ).first()

        if existing:
            logger.info(f"Found exact name+location match for {name}: {existing.name} (ID: {existing.id})")
            return existing.id, 0.95, "name_location_exact"

    # Method 3: Fuzzy name matching with location
    if name and (city or state):
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
    threshold: float = 0.85,
    community_id: Optional[int] = None
) -> Tuple[Optional[int], Optional[float], Optional[str]]:
    """
    Search for duplicate builder in database with location-aware matching.

    Matching criteria (in priority order):
    1. Exact name + community match (confidence: 1.0) - highest priority for location accuracy
    2. Exact website URL match + location validation (confidence: 0.98)
    3. Exact email match + location validation (confidence: 0.95)
    4. Exact phone match + location validation (confidence: 0.93)
    5. Exact name + location match (confidence: 0.90)
    6. Fuzzy name match + location + service area validation (confidence: varies)

    Location validation ensures that:
    - Builder serves the community being collected
    - Builder's service areas include the collection location
    - For multi-location builders, we match the correct office/location

    Args:
        db: Database session
        name: Builder name
        city: City name
        state: State code
        website: Website URL
        phone: Phone number
        email: Email address
        threshold: Minimum similarity score (0.0-1.0)
        community_id: Community ID from collection context (for location validation)

    Returns:
        Tuple of (entity_id, confidence_score, match_method) or (None, None, None)
    """
    from model.profiles.builder import BuilderProfile, builder_communities
    from sqlalchemy import select

    # Method 1: Exact name + community match (highest confidence for location accuracy)
    # This prevents matching national builders by name alone without location validation
    if community_id and name:
        # Find builders linked to this specific community
        builders_in_community = db.execute(
            select(BuilderProfile).join(
                builder_communities,
                BuilderProfile.id == builder_communities.c.builder_id
            ).where(
                builder_communities.c.community_id == community_id,
                func.lower(BuilderProfile.name) == name.lower().strip()
            )
        ).scalars().all()

        if builders_in_community:
            # Found exact match: same name AND linked to the same community
            builder = builders_in_community[0]
            logger.info(f"Found exact name+community match for builder {name}: {builder.name} (ID: {builder.id}) in community {community_id}")
            return builder.id, 1.0, "name_community_exact"

    # Method 2: Exact website match + location validation
    if website:
        normalized_website = website.lower().strip().rstrip('/')
        candidates = db.query(BuilderProfile).filter(
            func.lower(BuilderProfile.website) == normalized_website
        ).all()

        if candidates:
            # For multi-location builders sharing same corporate website,
            # validate location to ensure we match the correct office
            for candidate in candidates:
                if validate_builder_location(db, candidate, community_id, city, state):
                    # Additional check: if community_id is provided, only return as duplicate
                    # if the builder is already linked to THIS specific community
                    # (same builder can exist in multiple communities in same city)
                    if community_id:
                        is_in_community = db.execute(
                            select(builder_communities).where(
                                builder_communities.c.builder_id == candidate.id,
                                builder_communities.c.community_id == community_id
                            )
                        ).first()

                        if is_in_community:
                            logger.info(f"Found exact website match with location validation for builder {name}: {candidate.name} (ID: {candidate.id}) in same community {community_id}")
                            return candidate.id, 0.98, "website_exact_location_validated"
                        else:
                            logger.info(f"Found builder {candidate.name} (ID: {candidate.id}) with same website but in different community - allowing creation")
                            continue
                    else:
                        # No community context, return match
                        logger.info(f"Found exact website match with location validation for builder {name}: {candidate.name} (ID: {candidate.id})")
                        return candidate.id, 0.98, "website_exact_location_validated"

            # If we found website matches but none passed location validation,
            # log a warning (likely different office/location of same builder)
            if candidates:
                logger.warning(f"Found {len(candidates)} website matches for {normalized_website} but none serve location {city}, {state} (community {community_id})")
                # Don't return a match - this could be a different office

    # Method 3: Exact email match + location validation
    if email:
        normalized_email = email.lower().strip()
        candidates = db.query(BuilderProfile).filter(
            func.lower(BuilderProfile.email) == normalized_email
        ).all()

        if candidates:
            # Validate location for email matches
            for candidate in candidates:
                if validate_builder_location(db, candidate, community_id, city, state):
                    logger.info(f"Found exact email match with location validation for builder {name}: {candidate.name} (ID: {candidate.id})")
                    return candidate.id, 0.95, "email_exact_location_validated"

            if candidates:
                logger.warning(f"Found {len(candidates)} email matches for {normalized_email} but none serve location {city}, {state} (community {community_id})")

    # Method 4: Exact phone match + location validation
    if phone:
        # Normalize phone number (remove spaces, dashes, parentheses)
        normalized_phone = ''.join(c for c in phone if c.isdigit())

        all_builders = db.query(BuilderProfile).filter(
            BuilderProfile.phone.isnot(None)
        ).all()

        matched_candidates = []
        for builder in all_builders:
            if builder.phone:
                builder_phone = ''.join(c for c in builder.phone if c.isdigit())
                if normalized_phone == builder_phone:
                    matched_candidates.append(builder)

        if matched_candidates:
            # Validate location for phone matches
            for candidate in matched_candidates:
                if validate_builder_location(db, candidate, community_id, city, state):
                    logger.info(f"Found exact phone match with location validation for builder {name}: {candidate.name} (ID: {candidate.id})")
                    return candidate.id, 0.93, "phone_exact_location_validated"

            logger.warning(f"Found {len(matched_candidates)} phone matches for {normalized_phone} but none serve location {city}, {state} (community {community_id})")

    # Method 5: Exact name + location match (with community validation if provided)
    if city and state:
        candidates = db.query(BuilderProfile).filter(
            func.lower(BuilderProfile.name) == name.lower().strip(),
            func.lower(BuilderProfile.city) == city.lower().strip(),
            func.lower(BuilderProfile.state) == state.upper().strip()
        ).all()

        if candidates:
            # If community_id provided, check if any candidate is already linked to THIS community
            if community_id:
                for candidate in candidates:
                    # Check if this builder is already linked to the specific community
                    is_in_community = db.execute(
                        select(builder_communities).where(
                            builder_communities.c.builder_id == candidate.id,
                            builder_communities.c.community_id == community_id
                        )
                    ).first()

                    if is_in_community:
                        logger.info(f"Found exact name+location+community match for builder {name}: {candidate.name} (ID: {candidate.id}) in community {community_id}")
                        return candidate.id, 0.90, "name_location_exact"

                # If we found name+location matches but none in this community, it's NOT a duplicate
                logger.info(f"Found {len(candidates)} name+location matches for {name} in {city}, {state} but none in community {community_id} - allowing creation")
                # Continue to next method
            else:
                # No community context, return first match
                existing = candidates[0]
                logger.info(f"Found exact name+location match for builder {name}: {existing.name} (ID: {existing.id})")
                return existing.id, 0.90, "name_location_exact"

    # Method 6: Fuzzy name matching with location + service area validation
    # Only match builders that serve the collection location
    if city or state:
        # Get all builders (we'll filter by location validation)
        all_builders = db.query(BuilderProfile).all()

        best_match = None
        best_score = 0.0

        for candidate in all_builders:
            # First check if builder serves this location
            if not validate_builder_location(db, candidate, community_id, city, state):
                continue

            # Calculate name similarity
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
            # If community_id provided, check if this builder is already linked to THIS community
            if community_id:
                is_in_community = db.execute(
                    select(builder_communities).where(
                        builder_communities.c.builder_id == best_match.id,
                        builder_communities.c.community_id == community_id
                    )
                ).first()

                if is_in_community:
                    logger.info(f"Found fuzzy match with location validation for builder {name}: {best_match.name} (ID: {best_match.id}, score: {best_score:.2f}) in community {community_id}")
                    return best_match.id, best_score, "name_fuzzy_location_validated"
                else:
                    logger.info(f"Found fuzzy match for {name}: {best_match.name} (ID: {best_match.id}, score: {best_score:.2f}) but in different community - allowing creation")
                    # Not a duplicate for this community
            else:
                # No community context, return match
                logger.info(f"Found fuzzy match with location validation for builder {name}: {best_match.name} (ID: {best_match.id}, score: {best_score:.2f})")
                return best_match.id, best_score, "name_fuzzy_location_validated"

    logger.info(f"No duplicate found for builder: {name} in location {city}, {state} (community {community_id})")
    return None, None, None
