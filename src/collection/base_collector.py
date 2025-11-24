"""
Base Collector Service

Provides common functionality for all data collectors.
"""
import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from anthropic import Anthropic
from sqlalchemy.orm import Session
from model.collection import CollectionJob, CollectionChange, EntityMatch, CollectionSource

logger = logging.getLogger(__name__)


class BaseCollector:
    """
    Base class for all data collectors.

    Provides common functionality:
    - Claude API integration
    - Job management
    - Change detection and recording
    - Entity matching
    - Error handling
    """

    def __init__(self, db: Session, job_id: str):
        """
        Initialize collector.

        Args:
            db: Database session
            job_id: The collection job ID
        """
        self.db = db
        self.job_id = job_id
        self.job = self._load_job()
        self.anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    def _load_job(self) -> CollectionJob:
        """Load the collection job from database."""
        job = self.db.query(CollectionJob).filter(
            CollectionJob.job_id == self.job_id
        ).first()

        if not job:
            raise ValueError(f"Job {self.job_id} not found")

        return job

    def update_job_status(self, status: str, **kwargs):
        """
        Update job status and metadata.

        Args:
            status: New status (pending, running, completed, failed)
            **kwargs: Additional fields to update
        """
        self.job.status = status

        if status == "running" and not self.job.started_at:
            self.job.started_at = datetime.utcnow()
        elif status in ["completed", "failed"]:
            self.job.completed_at = datetime.utcnow()

        for key, value in kwargs.items():
            if hasattr(self.job, key):
                setattr(self.job, key, value)

        self.db.commit()
        logger.info(f"Job {self.job_id} status updated to {status}")

    def call_claude(self, prompt: str, max_tokens: int = 4096) -> Dict[str, Any]:
        """
        Call Claude API with a prompt.

        Args:
            prompt: The prompt to send to Claude
            max_tokens: Maximum tokens in response

        Returns:
            Parsed JSON response from Claude
        """
        try:
            message = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=max_tokens,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Extract text content
            response_text = message.content[0].text

            # Try to parse as JSON
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                # If not valid JSON, return as text
                return {"raw_response": response_text}

        except Exception as e:
            logger.error(f"Claude API call failed: {str(e)}")
            raise

    def record_change(
        self,
        entity_type: str,
        entity_id: Optional[int],
        change_type: str,
        field_name: Optional[str] = None,
        old_value: Optional[Any] = None,
        new_value: Optional[Any] = None,
        is_new_entity: bool = False,
        proposed_entity_data: Optional[Dict] = None,
        confidence: float = 1.0,
        source_url: Optional[str] = None
    ) -> CollectionChange:
        """
        Record a detected change for admin review.

        Args:
            entity_type: Type of entity (builder, community, property, sales_rep)
            entity_id: ID of existing entity (None for new entities)
            change_type: Type of change (added, modified, removed)
            field_name: Name of field being changed
            old_value: Current value in database
            new_value: Proposed new value
            is_new_entity: True if this is a new entity creation
            proposed_entity_data: Full data for new entity
            confidence: Confidence score (0.0-1.0)
            source_url: URL where data was found

        Returns:
            The created CollectionChange record
        """
        # Convert complex values to JSON strings
        if old_value is not None and not isinstance(old_value, str):
            old_value = json.dumps(old_value)
        if new_value is not None and not isinstance(new_value, str):
            new_value = json.dumps(new_value)

        change = CollectionChange(
            job_id=self.job_id,
            entity_type=entity_type,
            entity_id=entity_id,
            is_new_entity=is_new_entity,
            proposed_entity_data=proposed_entity_data,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            change_type=change_type,
            confidence=confidence,
            source_url=source_url
        )

        self.db.add(change)
        self.db.commit()

        # Update job's changes_detected count
        self.job.changes_detected += 1
        self.db.commit()

        logger.info(
            f"Recorded change for {entity_type} "
            f"(entity_id={entity_id}, field={field_name}, type={change_type})"
        )

        return change

    def find_entity_match(
        self,
        discovered_entity_type: str,
        discovered_name: str,
        discovered_data: Dict,
        discovered_location: Optional[str] = None
    ) -> Optional[Tuple[int, float, str]]:
        """
        Find matching entity in database.

        Args:
            discovered_entity_type: Type of discovered entity
            discovered_name: Name of discovered entity
            discovered_data: Full discovered data
            discovered_location: Location context

        Returns:
            Tuple of (entity_id, confidence, match_method) if found, None otherwise
        """
        # This is a basic implementation - subclasses should override
        # with entity-specific matching logic

        # For now, just do exact name matching
        # TODO: Implement fuzzy matching, website matching, etc.

        return None

    def record_entity_match(
        self,
        discovered_entity_type: str,
        discovered_name: str,
        discovered_data: Dict,
        matched_entity_id: Optional[int] = None,
        match_confidence: Optional[float] = None,
        match_method: Optional[str] = None,
        discovered_location: Optional[str] = None
    ) -> EntityMatch:
        """
        Record an entity match for admin review.

        Args:
            discovered_entity_type: Type of discovered entity
            discovered_name: Name of discovered entity
            discovered_data: Full discovered data
            matched_entity_id: ID of matched existing entity (None if no match)
            match_confidence: Confidence score (0.0-1.0)
            match_method: Method used for matching
            discovered_location: Location context

        Returns:
            The created EntityMatch record
        """
        match = EntityMatch(
            discovered_entity_type=discovered_entity_type,
            discovered_name=discovered_name,
            discovered_location=discovered_location,
            discovered_data=discovered_data,
            matched_entity_type=discovered_entity_type if matched_entity_id else None,
            matched_entity_id=matched_entity_id,
            match_confidence=match_confidence,
            match_method=match_method,
            job_id=self.job_id
        )

        self.db.add(match)
        self.db.commit()

        logger.info(
            f"Recorded entity match for {discovered_name} "
            f"(matched_id={matched_entity_id}, confidence={match_confidence})"
        )

        return match

    def run(self):
        """
        Main execution method - must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement run()")
