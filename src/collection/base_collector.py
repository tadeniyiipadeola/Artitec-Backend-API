"""
Base Collector Service

Provides common functionality for all data collectors.
"""
import os
import json
import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from anthropic import Anthropic
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, DBAPIError
from model.collection import CollectionJob, CollectionChange, EntityMatch, CollectionSource, CollectionJobLog

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

    def _db_commit_with_retry(self, max_retries: int = 3, initial_delay: float = 1.0) -> bool:
        """
        Commit database transaction with retry logic and exponential backoff.

        Args:
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay in seconds before first retry

        Returns:
            True if commit successful, False otherwise

        Raises:
            Exception: If all retries exhausted
        """
        delay = initial_delay

        for attempt in range(max_retries):
            try:
                self.db.commit()
                return True
            except (OperationalError, DBAPIError) as e:
                error_msg = str(e)

                # Check if it's a connection/timeout error
                is_connection_error = any(err in error_msg.lower() for err in [
                    'connection', 'timeout', 'timed out', 'can\'t connect',
                    'lost connection', 'server has gone away'
                ])

                if is_connection_error and attempt < max_retries - 1:
                    logger.warning(
                        f"Database connection error on attempt {attempt + 1}/{max_retries}: {error_msg}. "
                        f"Retrying in {delay}s..."
                    )

                    # Rollback failed transaction
                    try:
                        self.db.rollback()
                    except Exception:
                        pass

                    # Wait before retry with exponential backoff
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff

                    # Try to refresh connection
                    try:
                        self.db.connection()
                    except Exception:
                        pass
                else:
                    # Not a connection error or final attempt - raise
                    logger.error(f"Database commit failed after {attempt + 1} attempts: {error_msg}")
                    self.db.rollback()
                    raise
            except Exception as e:
                # Non-DB error - rollback and raise immediately
                logger.error(f"Unexpected error during commit: {str(e)}")
                try:
                    self.db.rollback()
                except Exception:
                    pass
                raise

        return False

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

    def update_progress(self, items_found: Optional[int] = None,
                       new_entities_found: Optional[int] = None,
                       changes_detected: Optional[int] = None):
        """
        Update job progress counts without changing status.
        Useful for providing incremental progress updates during long-running jobs.

        Args:
            items_found: Total items found so far
            new_entities_found: New entities created so far
            changes_detected: Changes detected so far
        """
        if items_found is not None:
            self.job.items_found = items_found
        if new_entities_found is not None:
            self.job.new_entities_found = new_entities_found
        if changes_detected is not None:
            self.job.changes_detected = changes_detected

        self.db.commit()
        logger.debug(f"Job {self.job_id} progress: items={self.job.items_found}, "
                    f"entities={self.job.new_entities_found}, changes={self.job.changes_detected}")

    def log(self, message: str, level: str = "INFO", stage: Optional[str] = None,
            log_data: Optional[Dict[str, Any]] = None):
        """
        Write a log entry to the database for this job.
        Logs are displayed in the admin UI for monitoring and debugging.

        Args:
            message: The log message
            level: Log level (DEBUG, INFO, SUCCESS, WARNING, ERROR)
            stage: Optional stage name (searching, parsing, matching, saving, etc.)
            log_data: Optional structured data (counts, URLs, errors, etc.)
        """
        log_entry = CollectionJobLog(
            job_id=self.job_id,
            level=level.upper(),
            message=message,
            stage=stage,
            log_data=log_data
        )
        self.db.add(log_entry)
        self.db.commit()

        # Also log to Python logger for backend monitoring
        log_func = getattr(logger, level.lower(), logger.info)
        log_func(f"[{self.job_id}] {message}")

    def call_claude(self, prompt: str, max_tokens: int = 4096, timeout: int = 300) -> Dict[str, Any]:
        """
        Call Claude API with a prompt.

        Args:
            prompt: The prompt to send to Claude
            max_tokens: Maximum tokens in response
            timeout: Timeout in seconds (default: 300s = 5 minutes)

        Returns:
            Parsed JSON response from Claude

        Raises:
            TimeoutError: If API call takes longer than timeout
            Exception: Other API errors
        """
        try:
            logger.info(f"Calling Claude API (max_tokens={max_tokens}, timeout={timeout}s)...")

            message = self.anthropic_client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=max_tokens,
                timeout=float(timeout),  # Anthropic client timeout
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            logger.info(f"Claude API call completed successfully")

            # Extract text content
            response_text = message.content[0].text

            # Try to parse as JSON
            try:
                # First try direct parsing
                return json.loads(response_text)
            except json.JSONDecodeError:
                # Try to extract JSON from markdown code blocks
                import re
                json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
                if json_match:
                    json_text = json_match.group(1)
                    try:
                        return json.loads(json_text)
                    except json.JSONDecodeError:
                        pass

                # Try to find any JSON object in the response
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_text = json_match.group(0)
                    try:
                        return json.loads(json_text)
                    except json.JSONDecodeError:
                        # Try to repair incomplete JSON (truncated response)
                        # Close any open arrays and objects
                        repaired = json_text.rstrip()
                        # Count open/close brackets
                        open_braces = repaired.count('{') - repaired.count('}')
                        open_brackets = repaired.count('[') - repaired.count(']')

                        # Close arrays first, then objects
                        for _ in range(open_brackets):
                            repaired += ']'
                        for _ in range(open_braces):
                            repaired += '}'

                        try:
                            parsed = json.loads(repaired)
                            logger.warning(f"Successfully repaired incomplete JSON (added {open_brackets} ] and {open_braces} }})")
                            return parsed
                        except json.JSONDecodeError:
                            pass

                # If still not valid JSON, return as text
                logger.warning("Could not parse Claude response as JSON")
                return {"raw_response": response_text}

        except TimeoutError as e:
            logger.error(f"Claude API call timed out after {timeout} seconds: {str(e)}")
            raise
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

        # Update job's changes_detected count
        self.job.changes_detected += 1

        # Commit both changes in a single transaction with retry logic
        try:
            self._db_commit_with_retry(max_retries=3, initial_delay=1.0)
            logger.info(
                f"Recorded change for {entity_type} "
                f"(entity_id={entity_id}, field={field_name}, type={change_type})"
            )
        except (OperationalError, DBAPIError) as e:
            error_msg = f"Database error recording change: {str(e)}"
            logger.error(error_msg)
            # Try to log the error to the database if possible
            try:
                self.log(error_msg, "ERROR", "saving", {"entity_type": entity_type, "change_type": change_type})
            except Exception:
                pass  # If logging fails, at least we logged to Python logger
            raise

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
