"""
Line-Based Lot Detector for Artitec
Detects lots by finding black dashed/straight lines that form 3-4 sided enclosures
Adapted to work with MinIO storage and Artitec database schema
"""
import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from PIL import Image
import io

from src.storage_service import storage_service


class LineLotDetector:
    """
    Detector that specifically looks for black dashed or straight lines
    forming 4-8 sided lot boundaries
    """

    def __init__(self):
        self.min_sides = 4  # Lots are typically at least 4-sided (quadrilaterals)
        self.max_sides = 8  # Allow up to 8 sides for irregular lot shapes

    def _load_image_from_minio(self, minio_path: str) -> np.ndarray:
        """
        Load image from MinIO storage

        Args:
            minio_path: MinIO path (e.g., 'phases/CMY-XXX/site-plan.jpg')

        Returns:
            NumPy array of the image in BGR format (OpenCV standard)
        """
        try:
            # Download file from MinIO to memory
            file_data = storage_service.download_file_to_memory(minio_path)

            # Load with PIL then convert to OpenCV format
            img = Image.open(io.BytesIO(file_data))
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Convert PIL Image to numpy array (RGB)
            image_rgb = np.array(img)

            # Convert RGB to BGR for OpenCV
            image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)

            return image_bgr

        except Exception as e:
            raise ValueError(f"Could not load image from MinIO path {minio_path}: {str(e)}")

    def _load_image_from_filesystem(self, file_path: str) -> np.ndarray:
        """
        Load image from local filesystem

        Args:
            file_path: Path to image file

        Returns:
            NumPy array of the image in BGR format
        """
        image = cv2.imread(str(file_path))
        if image is None:
            raise ValueError(f"Could not load image from {file_path}")
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

    def _detect_black_lines(self, image: np.ndarray) -> Tuple[np.ndarray, List]:
        """
        Detect black dashed and straight lines in the image, filtering out text

        Args:
            image: Input phase map image (BGR format)

        Returns:
            Tuple of (binary mask of lines, list of detected lines)
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Threshold to find black lines (inverse threshold)
        _, black_mask = cv2.threshold(gray, 80, 255, cv2.THRESH_BINARY_INV)

        # Remove small noise that could be text
        # Text typically has small, thin strokes
        kernel_small = np.ones((2, 2), np.uint8)
        black_mask = cv2.morphologyEx(black_mask, cv2.MORPH_OPEN, kernel_small)

        # Apply edge detection to find line edges
        edges = cv2.Canny(black_mask, 50, 150)

        # Detect lines using Hough Line Transform
        # Parameters tuned for lot boundary lines (longer than text)
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=40,  # Higher threshold to avoid text
            minLineLength=50,  # Longer minimum to filter out text strokes
            maxLineGap=20  # Allow gaps for dashed lines
        )

        # Create line mask
        line_mask = np.zeros_like(gray)
        detected_lines = []

        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]

                # Calculate line length
                length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)

                # Filter out very short lines (likely text)
                if length < 40:
                    continue

                # Calculate line angle
                angle = np.abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)

                # Keep mostly horizontal (0°, 180°) or vertical (90°) lines
                # Lot boundaries are typically aligned, not at random angles like text
                is_horizontal = angle < 15 or angle > 165
                is_vertical = 75 < angle < 105

                # Allow some diagonal lines too (for angled lots)
                is_diagonal = 30 < angle < 60 or 120 < angle < 150

                if is_horizontal or is_vertical or is_diagonal:
                    cv2.line(line_mask, (x1, y1), (x2, y2), 255, 2)
                    detected_lines.append(((x1, y1), (x2, y2)))

        return line_mask, detected_lines

    def _find_enclosed_shapes(self, line_mask: np.ndarray) -> List[np.ndarray]:
        """
        Find shapes enclosed by detected lines

        Args:
            line_mask: Binary mask of detected lines

        Returns:
            List of contours representing enclosed shapes
        """
        # Dilate lines slightly to close small gaps in dashed lines
        kernel = np.ones((3, 3), np.uint8)
        dilated = cv2.dilate(line_mask, kernel, iterations=2)

        # Find contours of enclosed areas
        contours, _ = cv2.findContours(
            dilated,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        return contours

    def _filter_by_sides(self, contour: np.ndarray) -> Tuple[bool, int]:
        """
        Check if contour has 4-8 sides and is not text-like

        Args:
            contour: Contour to check

        Returns:
            Tuple of (is_valid, num_sides)
        """
        # Approximate polygon
        epsilon = 0.02 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)
        num_sides = len(approx)

        # Must have 4-8 sides
        if not (self.min_sides <= num_sides <= self.max_sides):
            return False, num_sides

        # Additional text filtering: check aspect ratio
        # Text creates very elongated shapes (high aspect ratio)
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = float(w) / h if h > 0 else 0

        # Lot boundaries should have aspect ratio between 0.2 and 5.0
        # Text often has extreme aspect ratios (very wide or very tall)
        if aspect_ratio < 0.2 or aspect_ratio > 5.0:
            return False, num_sides

        # Check if shape is too small (likely text)
        # Most real lots are at least 50x50 pixels
        if w < 50 or h < 50:
            return False, num_sides

        return True, num_sides

    def detect_lots(
        self,
        image_source: str,
        from_minio: bool = True,
        min_area: float = 200.0,
        max_area: float = 50000.0
    ) -> Dict:
        """
        Detect lots by finding black dashed/straight lines forming 4-8 sided shapes

        Args:
            image_source: MinIO path or filesystem path to phase map
            from_minio: If True, load from MinIO; if False, load from filesystem
            min_area: Minimum lot area in pixels
            max_area: Maximum lot area in pixels

        Returns:
            Dictionary with detected lots and metadata
        """
        print(f"Loading image from: {image_source} (MinIO: {from_minio})")
        image, (width, height) = self.load_image(image_source, from_minio)
        print(f"Image size: {width}x{height}")

        # Step 1: Detect black lines (dashed and straight)
        line_mask, detected_lines = self._detect_black_lines(image)
        print(f"Detected {len(detected_lines)} line segments")

        # Step 2: Find enclosed shapes
        contours = self._find_enclosed_shapes(line_mask)
        print(f"Found {len(contours)} potential enclosed shapes")

        # Step 3: Filter by number of sides and area
        detected_lots = []
        shapes_checked = 0

        for contour in contours:
            area = cv2.contourArea(contour)

            # Filter by area first
            if area < min_area or area > max_area:
                continue

            # Check number of sides
            is_valid, num_sides = self._filter_by_sides(contour)
            if not is_valid:
                continue

            shapes_checked += 1

            # Approximate polygon for cleaner boundaries
            epsilon = 0.01 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)

            # Calculate centroid
            M = cv2.moments(contour)
            if M['m00'] != 0:
                cx = int(M['m10'] / M['m00'])
                cy = int(M['m01'] / M['m00'])
            else:
                cx, cy = 0, 0

            # Convert to polygon format
            polygon = [{'x': int(pt[0][0]), 'y': int(pt[0][1])} for pt in approx]

            detected_lots.append({
                'polygon': polygon,
                'centroid': {'x': cx, 'y': cy},
                'area': float(area),
                'num_sides': num_sides,
                'detection_method': 'line_detection',
                'confidence': 0.75,  # Constant confidence for line-based detection
                'lot_number': None,  # Will be filled later
            })

        print(f"Checked {shapes_checked} shapes with {self.min_sides}-{self.max_sides} sides")
        print(f"Found {len(detected_lots)} valid lots")

        # Sort by position (top-left to bottom-right)
        detected_lots.sort(key=lambda x: (x['centroid']['y'], x['centroid']['x']))

        # Auto-assign lot numbers based on position
        for idx, lot in enumerate(detected_lots, start=1):
            lot['lot_number'] = str(idx)

        return {
            'lots': detected_lots,
            'lines_detected': len(detected_lines),
            'shapes_found': len(contours),
            'lots_detected': len(detected_lots),
            'model_type': 'Line Detection',
            'average_confidence': 0.75,
            'image_dimensions': {'width': width, 'height': height}
        }
