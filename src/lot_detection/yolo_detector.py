"""
YOLOv8-Based Lot Detector for Artitec
Provides highest accuracy lot detection using deep learning
Adapted to work with MinIO storage and Artitec database schema
"""
import cv2
import numpy as np
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import fitz  # PyMuPDF for PDF support
from PIL import Image
import io
import tempfile

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

from src.storage_service import storage_service


class YOLOLotDetector:
    """
    High-accuracy lot detector using YOLOv8 segmentation
    Supports: JPG, PNG, TIFF, PDF from MinIO or local filesystem
    """

    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize YOLO detector

        Args:
            model_path: Path to trained model. If None, uses pre-trained base model
        """
        if not YOLO_AVAILABLE:
            raise ImportError(
                "ultralytics package not installed. "
                "Install with: pip install ultralytics"
            )

        # Use custom trained model or start with base segmentation model
        self.model_path = model_path or 'yolov8n-seg.pt'
        self.model = YOLO(self.model_path)
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.pdf'}

    def _load_image_from_minio(self, minio_path: str) -> np.ndarray:
        """
        Load image from MinIO storage

        Args:
            minio_path: MinIO path (e.g., 'phases/CMY-XXX/site-plan.jpg')

        Returns:
            NumPy array of the image
        """
        try:
            # Download file from MinIO to memory
            file_data = storage_service.download_file_to_memory(minio_path)

            # Determine file type from extension
            extension = Path(minio_path).suffix.lower()

            if extension == '.pdf':
                # Handle PDF files
                doc = fitz.open(stream=file_data, filetype="pdf")
                if len(doc) == 0:
                    raise ValueError("PDF has no pages")

                # Convert first page to image at high resolution
                page = doc[0]
                pix = page.get_pixmap(dpi=300)

                # Convert to PIL Image then to numpy array
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                image = np.array(img)
                doc.close()
            else:
                # Handle standard image formats
                img = Image.open(io.BytesIO(file_data))
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                image = np.array(img)

            return image

        except Exception as e:
            raise ValueError(f"Could not load image from MinIO path {minio_path}: {str(e)}")

    def _load_image_from_filesystem(self, file_path: str) -> np.ndarray:
        """
        Load image from local filesystem

        Args:
            file_path: Path to image or PDF file

        Returns:
            NumPy array of the image
        """
        path = Path(file_path)
        extension = path.suffix.lower()

        if extension not in self.supported_formats:
            raise ValueError(
                f"Unsupported format {extension}. "
                f"Supported: {', '.join(self.supported_formats)}"
            )

        # Handle PDF files
        if extension == '.pdf':
            doc = fitz.open(str(path))
            if len(doc) == 0:
                raise ValueError("PDF has no pages")

            # Convert first page to image at high resolution
            page = doc[0]
            pix = page.get_pixmap(dpi=300)

            # Convert to PIL Image then to numpy array
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            image = np.array(img)
            doc.close()
        else:
            # Handle standard image formats
            image = cv2.imread(str(path))
            if image is None:
                raise ValueError(f"Could not load image from {file_path}")
            # Convert BGR to RGB for consistency
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        return image

    def load_image(self, image_source: str, from_minio: bool = True) -> Tuple[np.ndarray, Tuple[int, int]]:
        """
        Load image from MinIO or filesystem

        Args:
            image_source: MinIO path or filesystem path
            from_minio: If True, load from MinIO; if False, load from filesystem

        Returns:
            Tuple of (image array, (width, height))
        """
        if from_minio:
            image = self._load_image_from_minio(image_source)
        else:
            image = self._load_image_from_filesystem(image_source)

        height, width = image.shape[:2]
        return image, (width, height)

    def detect_lots(
        self,
        image_source: str,
        from_minio: bool = True,
        confidence_threshold: float = 0.25,
        min_area: float = 500.0,
        max_area: float = 50000.0
    ) -> Dict:
        """
        Detect lots using YOLOv8 segmentation

        Args:
            image_source: MinIO path or filesystem path to phase map
            from_minio: If True, load from MinIO; if False, load from filesystem
            confidence_threshold: Minimum confidence for detection (0-1)
            min_area: Minimum lot area in pixels
            max_area: Maximum lot area in pixels

        Returns:
            Dictionary with detected lots and metadata
        """
        print(f"Loading image from: {image_source} (MinIO: {from_minio})")
        image, (width, height) = self.load_image(image_source, from_minio)
        print(f"Image size: {width}x{height}")

        # Run YOLO inference
        print("Running YOLO detection...")
        results = self.model.predict(
            image,
            conf=confidence_threshold,
            verbose=False
        )

        detected_lots = []
        total_detections = 0

        # Process results
        for result in results:
            if result.masks is None:
                continue

            masks = result.masks.data.cpu().numpy()
            boxes = result.boxes.data.cpu().numpy()

            total_detections = len(masks)

            for idx, (mask, box) in enumerate(zip(masks, boxes)):
                confidence = float(box[4])

                # Resize mask to original image size
                mask_resized = cv2.resize(
                    mask,
                    (width, height),
                    interpolation=cv2.INTER_LINEAR
                )

                # Convert mask to binary
                binary_mask = (mask_resized > 0.5).astype(np.uint8)

                # Find contours
                contours, _ = cv2.findContours(
                    binary_mask,
                    cv2.RETR_EXTERNAL,
                    cv2.CHAIN_APPROX_SIMPLE
                )

                if len(contours) == 0:
                    continue

                # Get largest contour
                contour = max(contours, key=cv2.contourArea)
                area = cv2.contourArea(contour)

                # Filter by area
                if area < min_area or area > max_area:
                    continue

                # Approximate polygon (simplify to 3-4 sides if possible)
                epsilon = 0.01 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)

                # Calculate centroid
                M = cv2.moments(contour)
                if M['m00'] != 0:
                    cx = int(M['m10'] / M['m00'])
                    cy = int(M['m01'] / M['m00'])
                else:
                    cx, cy = int(box[0]), int(box[1])

                # Convert to polygon format
                polygon = [{'x': int(pt[0][0]), 'y': int(pt[0][1])} for pt in approx]

                detected_lots.append({
                    'polygon': polygon,
                    'centroid': {'x': cx, 'y': cy},
                    'area': float(area),
                    'num_sides': len(approx),
                    'confidence': confidence,
                    'detection_method': 'yolo',
                    'lot_number': None
                })

        # Sort by position (top-left to bottom-right)
        detected_lots.sort(key=lambda x: (x['centroid']['y'], x['centroid']['x']))

        # Auto-assign lot numbers based on position
        for idx, lot in enumerate(detected_lots, start=1):
            lot['lot_number'] = str(idx)

        print(f"Total detections: {total_detections}")
        print(f"After filtering: {len(detected_lots)} valid lots")

        return {
            'lots': detected_lots,
            'total_detections': total_detections,
            'lots_detected': len(detected_lots),
            'model_type': 'YOLOv8',
            'confidence_threshold': confidence_threshold,
            'average_confidence': sum(lot['confidence'] for lot in detected_lots) / len(detected_lots) if detected_lots else 0,
            'image_dimensions': {'width': width, 'height': height}
        }

    def train_on_data(
        self,
        dataset_yaml: str,
        epochs: int = 100,
        image_size: int = 1024,
        batch_size: int = 8
    ):
        """
        Train YOLO model on custom phase map dataset

        Args:
            dataset_yaml: Path to dataset configuration YAML
            epochs: Number of training epochs
            image_size: Training image size
            batch_size: Batch size for training

        Returns:
            Training results
        """
        print(f"Training YOLOv8 model...")
        print(f"Dataset: {dataset_yaml}")
        print(f"Epochs: {epochs}, Image size: {image_size}")

        results = self.model.train(
            data=dataset_yaml,
            epochs=epochs,
            imgsz=image_size,
            batch=batch_size,
            name='artitec_lot_detector',
            patience=20,  # Early stopping
            save=True,
            device='mps' if self._has_mps() else 'cpu'  # Use Apple Silicon if available
        )

        return results

    def _has_mps(self) -> bool:
        """Check if Apple Silicon MPS is available"""
        try:
            import torch
            return torch.backends.mps.is_available()
        except:
            return False


# Fallback message if YOLO not available
if not YOLO_AVAILABLE:
    print("Warning: YOLOv8 not available. Install with: pip install ultralytics")
    print("Falling back to LineLotDetector for lot detection.")
