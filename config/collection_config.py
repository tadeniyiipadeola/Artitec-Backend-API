"""
Collection system configuration.
Defines concurrency limits, timeouts, and other collection-related settings.
"""

import os


class CollectionConfig:
    """
    Centralized collection configuration.
    """

    # ============================================================================
    # CONCURRENCY LIMITS
    # ============================================================================

    # Maximum number of concurrent jobs by entity type
    # Lower numbers = more conservative, less load
    # Higher numbers = faster overall throughput, more load

    MAX_CONCURRENT_COMMUNITY_JOBS: int = int(os.getenv('MAX_CONCURRENT_COMMUNITY_JOBS', '1'))
    MAX_CONCURRENT_BUILDER_JOBS: int = int(os.getenv('MAX_CONCURRENT_BUILDER_JOBS', '5'))
    MAX_CONCURRENT_PROPERTY_JOBS: int = int(os.getenv('MAX_CONCURRENT_PROPERTY_JOBS', '10'))
    MAX_CONCURRENT_SALES_REP_JOBS: int = int(os.getenv('MAX_CONCURRENT_SALES_REP_JOBS', '5'))

    # Global maximum concurrent jobs (across all types)
    MAX_TOTAL_CONCURRENT_JOBS: int = int(os.getenv('MAX_TOTAL_CONCURRENT_JOBS', '15'))

    # ============================================================================
    # TIMEOUT SETTINGS
    # ============================================================================

    # Claude API timeout (seconds)
    CLAUDE_API_TIMEOUT: int = int(os.getenv('CLAUDE_API_TIMEOUT', '300'))  # 5 minutes

    # Maximum job execution time by entity type (seconds)
    # Jobs exceeding these limits will be marked as failed
    JOB_TIMEOUT_COMMUNITY: int = int(os.getenv('JOB_TIMEOUT_COMMUNITY', '1800'))  # 30 minutes
    JOB_TIMEOUT_BUILDER: int = int(os.getenv('JOB_TIMEOUT_BUILDER', '600'))  # 10 minutes
    JOB_TIMEOUT_PROPERTY: int = int(os.getenv('JOB_TIMEOUT_PROPERTY', '900'))  # 15 minutes
    JOB_TIMEOUT_SALES_REP: int = int(os.getenv('JOB_TIMEOUT_SALES_REP', '600'))  # 10 minutes

    # ============================================================================
    # RETRY SETTINGS
    # ============================================================================

    # Maximum retry attempts for failed jobs
    MAX_RETRY_ATTEMPTS: int = int(os.getenv('MAX_RETRY_ATTEMPTS', '3'))

    # Retry delay (seconds) - doubles with each retry
    RETRY_DELAY_BASE: int = int(os.getenv('RETRY_DELAY_BASE', '60'))  # Start at 1 minute

    # ============================================================================
    # JOB EXECUTOR SETTINGS
    # ============================================================================

    # Job executor polling interval (seconds)
    # How often the executor checks for new pending jobs
    EXECUTOR_POLL_INTERVAL: int = int(os.getenv('EXECUTOR_POLL_INTERVAL', '10'))

    # Job executor batch size
    # Maximum number of jobs to fetch per poll
    EXECUTOR_BATCH_SIZE: int = int(os.getenv('EXECUTOR_BATCH_SIZE', '50'))

    # Enable auto-execution of pending jobs
    AUTO_EXECUTE_JOBS: bool = os.getenv('AUTO_EXECUTE_JOBS', 'true').lower() == 'true'

    # ============================================================================
    # PRIORITY SETTINGS
    # ============================================================================

    # Job priority levels
    # Higher priority jobs are executed first
    PRIORITY_HIGH: int = 10
    PRIORITY_MEDIUM: int = 5
    PRIORITY_LOW: int = 1

    # Default priorities by entity type
    DEFAULT_PRIORITY_COMMUNITY: int = 8
    DEFAULT_PRIORITY_BUILDER: int = 6
    DEFAULT_PRIORITY_PROPERTY: int = 3
    DEFAULT_PRIORITY_SALES_REP: int = 5

    # ============================================================================
    # DATA QUALITY SETTINGS
    # ============================================================================

    # Minimum confidence threshold for auto-applying changes
    AUTO_APPLY_CONFIDENCE_THRESHOLD: float = float(os.getenv('AUTO_APPLY_CONFIDENCE_THRESHOLD', '0.95'))

    # Require manual review for changes below this threshold
    MANUAL_REVIEW_CONFIDENCE_THRESHOLD: float = float(os.getenv('MANUAL_REVIEW_CONFIDENCE_THRESHOLD', '0.8'))

    # ============================================================================
    # HELPER METHODS
    # ============================================================================

    @staticmethod
    def get_max_concurrent_jobs(entity_type: str) -> int:
        """
        Get maximum concurrent jobs for entity type.

        Args:
            entity_type: Entity type (community, builder, property, sales_rep)

        Returns:
            Maximum concurrent jobs allowed for this entity type
        """
        limits = {
            'community': CollectionConfig.MAX_CONCURRENT_COMMUNITY_JOBS,
            'builder': CollectionConfig.MAX_CONCURRENT_BUILDER_JOBS,
            'property': CollectionConfig.MAX_CONCURRENT_PROPERTY_JOBS,
            'sales_rep': CollectionConfig.MAX_CONCURRENT_SALES_REP_JOBS,
        }
        return limits.get(entity_type, 1)

    @staticmethod
    def get_job_timeout(entity_type: str) -> int:
        """
        Get job timeout for entity type.

        Args:
            entity_type: Entity type (community, builder, property, sales_rep)

        Returns:
            Timeout in seconds
        """
        timeouts = {
            'community': CollectionConfig.JOB_TIMEOUT_COMMUNITY,
            'builder': CollectionConfig.JOB_TIMEOUT_BUILDER,
            'property': CollectionConfig.JOB_TIMEOUT_PROPERTY,
            'sales_rep': CollectionConfig.JOB_TIMEOUT_SALES_REP,
        }
        return timeouts.get(entity_type, 600)

    @staticmethod
    def get_default_priority(entity_type: str) -> int:
        """
        Get default priority for entity type.

        Args:
            entity_type: Entity type (community, builder, property, sales_rep)

        Returns:
            Default priority level
        """
        priorities = {
            'community': CollectionConfig.DEFAULT_PRIORITY_COMMUNITY,
            'builder': CollectionConfig.DEFAULT_PRIORITY_BUILDER,
            'property': CollectionConfig.DEFAULT_PRIORITY_PROPERTY,
            'sales_rep': CollectionConfig.DEFAULT_PRIORITY_SALES_REP,
        }
        return priorities.get(entity_type, CollectionConfig.PRIORITY_MEDIUM)


# Export configuration as module-level constants for easy import
MAX_CONCURRENT_COMMUNITY_JOBS = CollectionConfig.MAX_CONCURRENT_COMMUNITY_JOBS
MAX_CONCURRENT_BUILDER_JOBS = CollectionConfig.MAX_CONCURRENT_BUILDER_JOBS
MAX_CONCURRENT_PROPERTY_JOBS = CollectionConfig.MAX_CONCURRENT_PROPERTY_JOBS
MAX_CONCURRENT_SALES_REP_JOBS = CollectionConfig.MAX_CONCURRENT_SALES_REP_JOBS
MAX_TOTAL_CONCURRENT_JOBS = CollectionConfig.MAX_TOTAL_CONCURRENT_JOBS

CLAUDE_API_TIMEOUT = CollectionConfig.CLAUDE_API_TIMEOUT
AUTO_EXECUTE_JOBS = CollectionConfig.AUTO_EXECUTE_JOBS
EXECUTOR_POLL_INTERVAL = CollectionConfig.EXECUTOR_POLL_INTERVAL
