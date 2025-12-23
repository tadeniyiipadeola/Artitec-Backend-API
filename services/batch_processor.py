"""
Batch Processor Service
Processes multiple site plan images in parallel using threading
Supports various detection methods and progress tracking
"""
import cv2
import numpy as np
from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import time
from enum import Enum


class ProcessingStatus(str, Enum):
    """Status of batch processing job"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DetectionMethod(str, Enum):
    """Available detection methods"""
    AUTO = "auto"
    OCR = "ocr"
    BOUNDARY = "boundary"
    LINE = "line"
    FEW_SHOT = "few_shot"
    SUPERVISED = "supervised"


@dataclass
class BatchItem:
    """Single item in batch processing"""
    image_path: str
    image_id: str  # Unique identifier
    status: ProcessingStatus = ProcessingStatus.PENDING
    progress: float = 0.0
    result: Optional[Dict] = None
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None


@dataclass
class BatchJob:
    """Batch processing job"""
    job_id: str
    items: List[BatchItem]
    detection_method: DetectionMethod
    parameters: Dict = field(default_factory=dict)
    status: ProcessingStatus = ProcessingStatus.PENDING
    progress: float = 0.0
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    total_items: int = 0
    completed_items: int = 0
    failed_items: int = 0


class BatchProcessor:
    """
    Batch processor for multiple site plan images

    Features:
    - Parallel processing using ThreadPoolExecutor
    - Progress tracking
    - Error handling and retry
    - Multiple detection methods
    - Result aggregation
    """

    def __init__(
        self,
        max_workers: int = 4,
        timeout: int = 300,  # 5 minutes per image
    ):
        """
        Initialize batch processor

        Args:
            max_workers: Maximum number of parallel workers
            timeout: Timeout per image in seconds
        """
        self.max_workers = max_workers
        self.timeout = timeout
        self.jobs: Dict[str, BatchJob] = {}
        self.lock = Lock()

    def create_job(
        self,
        image_paths: List[str],
        detection_method: DetectionMethod,
        parameters: Optional[Dict] = None,
    ) -> str:
        """
        Create a new batch processing job

        Args:
            image_paths: List of image file paths
            detection_method: Detection method to use
            parameters: Additional parameters for detection

        Returns:
            Job ID
        """
        import uuid

        job_id = str(uuid.uuid4())

        # Create batch items
        items = []
        for i, image_path in enumerate(image_paths):
            items.append(BatchItem(
                image_path=image_path,
                image_id=f"{job_id}_{i}",
            ))

        # Create job
        job = BatchJob(
            job_id=job_id,
            items=items,
            detection_method=detection_method,
            parameters=parameters or {},
            total_items=len(items),
        )

        with self.lock:
            self.jobs[job_id] = job

        return job_id

    def process_job(
        self,
        job_id: str,
        detector_func: Callable[[np.ndarray, Dict], Any],
    ) -> BatchJob:
        """
        Process a batch job

        Args:
            job_id: Job identifier
            detector_func: Detection function to apply
                          Should take (image, parameters) and return results

        Returns:
            Completed job with results
        """
        if job_id not in self.jobs:
            raise ValueError(f"Job {job_id} not found")

        job = self.jobs[job_id]

        # Update job status
        with self.lock:
            job.status = ProcessingStatus.PROCESSING
            job.started_at = time.time()

        # Process items in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_item = {
                executor.submit(
                    self._process_single_item,
                    item,
                    detector_func,
                    job.parameters,
                ): item
                for item in job.items
            }

            # Collect results as they complete
            for future in as_completed(future_to_item, timeout=self.timeout * len(job.items)):
                item = future_to_item[future]

                try:
                    result = future.result(timeout=self.timeout)

                    with self.lock:
                        if result['status'] == 'success':
                            item.status = ProcessingStatus.COMPLETED
                            item.result = result['data']
                            job.completed_items += 1
                        else:
                            item.status = ProcessingStatus.FAILED
                            item.error = result.get('error', 'Unknown error')
                            job.failed_items += 1

                        item.end_time = time.time()

                        # Update job progress
                        job.progress = (job.completed_items + job.failed_items) / job.total_items

                except Exception as e:
                    with self.lock:
                        item.status = ProcessingStatus.FAILED
                        item.error = str(e)
                        item.end_time = time.time()
                        job.failed_items += 1
                        job.progress = (job.completed_items + job.failed_items) / job.total_items

        # Mark job as completed
        with self.lock:
            job.status = ProcessingStatus.COMPLETED
            job.completed_at = time.time()
            job.progress = 1.0

        return job

    def _process_single_item(
        self,
        item: BatchItem,
        detector_func: Callable,
        parameters: Dict,
    ) -> Dict:
        """
        Process a single batch item

        Args:
            item: Batch item to process
            detector_func: Detection function
            parameters: Detection parameters

        Returns:
            Result dictionary
        """
        try:
            with self.lock:
                item.status = ProcessingStatus.PROCESSING
                item.start_time = time.time()

            # Read image
            image = cv2.imread(item.image_path)
            if image is None:
                return {
                    'status': 'error',
                    'error': f"Could not read image: {item.image_path}"
                }

            # Apply detection
            result = detector_func(image, parameters)

            return {
                'status': 'success',
                'data': result,
            }

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
            }

    def get_job_status(self, job_id: str) -> Dict:
        """
        Get current status of a job

        Args:
            job_id: Job identifier

        Returns:
            Job status information
        """
        if job_id not in self.jobs:
            raise ValueError(f"Job {job_id} not found")

        job = self.jobs[job_id]

        with self.lock:
            return {
                'job_id': job.job_id,
                'status': job.status,
                'progress': job.progress,
                'total_items': job.total_items,
                'completed_items': job.completed_items,
                'failed_items': job.failed_items,
                'created_at': job.created_at,
                'started_at': job.started_at,
                'completed_at': job.completed_at,
                'elapsed_time': (
                    (job.completed_at or time.time()) - job.started_at
                    if job.started_at else 0
                ),
            }

    def get_job_results(self, job_id: str) -> Dict:
        """
        Get results of a completed job

        Args:
            job_id: Job identifier

        Returns:
            Job results
        """
        if job_id not in self.jobs:
            raise ValueError(f"Job {job_id} not found")

        job = self.jobs[job_id]

        with self.lock:
            results = []
            for item in job.items:
                results.append({
                    'image_id': item.image_id,
                    'image_path': item.image_path,
                    'status': item.status,
                    'result': item.result,
                    'error': item.error,
                    'processing_time': (
                        item.end_time - item.start_time
                        if item.start_time and item.end_time else None
                    ),
                })

            return {
                'job_id': job.job_id,
                'status': job.status,
                'total_items': job.total_items,
                'completed_items': job.completed_items,
                'failed_items': job.failed_items,
                'results': results,
            }

    def cancel_job(self, job_id: str):
        """
        Cancel a running job

        Args:
            job_id: Job identifier
        """
        if job_id not in self.jobs:
            raise ValueError(f"Job {job_id} not found")

        # Note: ThreadPoolExecutor doesn't support cancellation well
        # This marks the job as failed
        with self.lock:
            job = self.jobs[job_id]
            if job.status == ProcessingStatus.PROCESSING:
                job.status = ProcessingStatus.FAILED
                for item in job.items:
                    if item.status == ProcessingStatus.PROCESSING or item.status == ProcessingStatus.PENDING:
                        item.status = ProcessingStatus.FAILED
                        item.error = "Job cancelled by user"

    def delete_job(self, job_id: str):
        """
        Delete a job

        Args:
            job_id: Job identifier
        """
        with self.lock:
            if job_id in self.jobs:
                del self.jobs[job_id]

    def list_jobs(self) -> List[Dict]:
        """
        List all jobs

        Returns:
            List of job summaries
        """
        with self.lock:
            summaries = []
            for job_id, job in self.jobs.items():
                summaries.append({
                    'job_id': job.job_id,
                    'status': job.status,
                    'progress': job.progress,
                    'total_items': job.total_items,
                    'completed_items': job.completed_items,
                    'failed_items': job.failed_items,
                    'created_at': job.created_at,
                    'detection_method': job.detection_method,
                })
            return summaries

    def get_aggregate_statistics(self, job_id: str) -> Dict:
        """
        Get aggregate statistics from batch results

        Args:
            job_id: Job identifier

        Returns:
            Aggregate statistics
        """
        if job_id not in self.jobs:
            raise ValueError(f"Job {job_id} not found")

        job = self.jobs[job_id]

        if job.status != ProcessingStatus.COMPLETED:
            raise ValueError(f"Job {job_id} not completed yet")

        with self.lock:
            # Collect all results
            all_lots = []
            total_area = 0
            total_confidence = 0
            methods_used = {}

            for item in job.items:
                if item.status == ProcessingStatus.COMPLETED and item.result:
                    lots = item.result.get('lots', [])
                    all_lots.extend(lots)

                    for lot in lots:
                        total_area += lot.get('area', 0)
                        total_confidence += lot.get('confidence', 0)

                        method = lot.get('detection_method', 'unknown')
                        methods_used[method] = methods_used.get(method, 0) + 1

            avg_area = total_area / len(all_lots) if all_lots else 0
            avg_confidence = total_confidence / len(all_lots) if all_lots else 0

            return {
                'total_lots_detected': len(all_lots),
                'total_images_processed': job.completed_items,
                'failed_images': job.failed_items,
                'average_lot_area': avg_area,
                'average_confidence': avg_confidence,
                'detection_methods': methods_used,
                'lots_per_image': len(all_lots) / job.completed_items if job.completed_items > 0 else 0,
            }


# Convenience functions for common detection methods

def create_auto_detect_processor(
    image_paths: List[str],
    use_ocr: bool = True,
    min_area: int = 1000,
) -> tuple[BatchProcessor, str]:
    """
    Create batch processor for auto-detection

    Args:
        image_paths: List of image paths
        use_ocr: Use OCR
        min_area: Minimum lot area

    Returns:
        Tuple of (processor, job_id)
    """
    from services.auto_detect_service import AutoDetectService

    processor = BatchProcessor()

    def detector_func(image: np.ndarray, params: Dict) -> Dict:
        service = AutoDetectService(min_area=params.get('min_area', 1000))
        lots = service.detect_lots(image, use_ocr=params.get('use_ocr', True))

        return {
            'lots': [
                {
                    'lot_number': lot.lot_number,
                    'coordinates': lot.coordinates,
                    'area': lot.area,
                    'confidence': lot.confidence,
                    'detection_method': lot.detection_method,
                }
                for lot in lots
            ]
        }

    job_id = processor.create_job(
        image_paths,
        DetectionMethod.AUTO,
        {'use_ocr': use_ocr, 'min_area': min_area},
    )

    # Start processing in background
    import threading
    thread = threading.Thread(
        target=processor.process_job,
        args=(job_id, detector_func),
    )
    thread.start()

    return processor, job_id
