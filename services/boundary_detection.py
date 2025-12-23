"""
Boundary Detection Service
Detects lot boundaries using edge detection and contour analysis
Uses OpenCV for image processing
"""
import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass


@dataclass
class BoundaryResult:
    """Result of boundary detection"""
    coordinates: List[Tuple[int, int]]  # Polygon vertices
    area: float
    perimeter: float
    confidence: float
    method: str = "edge_detection"


class BoundaryDetectionService:
    """
    Service for detecting lot boundaries using edge detection

    Features:
    - Canny edge detection
    - Contour extraction
    - Polygon approximation
    - Area-based filtering
    - Grid-based detection option
    """

    def __init__(
        self,
        min_area: int = 1000,
        max_area: Optional[int] = None,
        edge_low_threshold: int = 50,
        edge_high_threshold: int = 150,
        approx_epsilon: float = 0.02,
    ):
        """
        Initialize boundary detection service

        Args:
            min_area: Minimum contour area to consider
            max_area: Maximum contour area (None = no limit)
            edge_low_threshold: Lower threshold for Canny edge detection
            edge_high_threshold: Upper threshold for Canny edge detection
            approx_epsilon: Epsilon for polygon approximation (as ratio of perimeter)
        """
        self.min_area = min_area
        self.max_area = max_area
        self.edge_low_threshold = edge_low_threshold
        self.edge_high_threshold = edge_high_threshold
        self.approx_epsilon = approx_epsilon

    def detect_boundaries(
        self,
        image: np.ndarray,
        use_grid: bool = False,
        grid_rows: Optional[int] = None,
        grid_cols: Optional[int] = None,
    ) -> List[BoundaryResult]:
        """
        Detect lot boundaries in an image

        Args:
            image: Input image (BGR or grayscale)
            use_grid: If True, use grid-based detection
            grid_rows: Number of grid rows (for grid mode)
            grid_cols: Number of grid columns (for grid mode)

        Returns:
            List of detected boundaries
        """
        if use_grid and grid_rows and grid_cols:
            return self._detect_grid_boundaries(image, grid_rows, grid_cols)
        else:
            return self._detect_edge_boundaries(image)

    def _detect_edge_boundaries(self, image: np.ndarray) -> List[BoundaryResult]:
        """
        Detect boundaries using edge detection and contour analysis

        Args:
            image: Input image

        Returns:
            List of detected boundaries
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Apply Canny edge detection
        edges = cv2.Canny(
            blurred,
            self.edge_low_threshold,
            self.edge_high_threshold,
        )

        # Dilate edges to connect nearby edges
        kernel = np.ones((3, 3), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=1)

        # Find contours
        contours, _ = cv2.findContours(
            dilated,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        # Process contours
        results = []
        for contour in contours:
            # Calculate area
            area = cv2.contourArea(contour)

            # Filter by area
            if area < self.min_area:
                continue
            if self.max_area and area > self.max_area:
                continue

            # Calculate perimeter
            perimeter = cv2.arcLength(contour, True)

            # Approximate polygon
            epsilon = self.approx_epsilon * perimeter
            approx = cv2.approxPolyDP(contour, epsilon, True)

            # Filter by polygon vertices (should be 4-8 sided)
            if len(approx) < 4 or len(approx) > 8:
                continue

            # Extract coordinates
            coordinates = [(int(point[0][0]), int(point[0][1])) for point in approx]

            # Calculate confidence based on area and vertex count
            # Prefer 4-sided polygons (rectangles)
            vertex_score = 1.0 if len(approx) == 4 else 0.8
            area_score = min(area / (self.max_area or area), 1.0)
            confidence = (vertex_score + area_score) / 2

            results.append(BoundaryResult(
                coordinates=coordinates,
                area=area,
                perimeter=perimeter,
                confidence=confidence,
                method="edge_detection",
            ))

        # Sort by confidence
        results.sort(key=lambda x: x.confidence, reverse=True)

        return results

    def _detect_grid_boundaries(
        self,
        image: np.ndarray,
        rows: int,
        cols: int,
    ) -> List[BoundaryResult]:
        """
        Detect boundaries using grid-based subdivision

        Useful for uniform lot layouts where lots are arranged in a grid

        Args:
            image: Input image
            rows: Number of grid rows
            cols: Number of grid columns

        Returns:
            List of grid-based boundaries
        """
        height, width = image.shape[:2]

        cell_height = height / rows
        cell_width = width / cols

        results = []

        for row in range(rows):
            for col in range(cols):
                # Calculate cell boundaries
                x1 = int(col * cell_width)
                y1 = int(row * cell_height)
                x2 = int((col + 1) * cell_width)
                y2 = int((row + 1) * cell_height)

                # Create rectangle coordinates
                coordinates = [
                    (x1, y1),
                    (x2, y1),
                    (x2, y2),
                    (x1, y2),
                ]

                area = cell_width * cell_height
                perimeter = 2 * (cell_width + cell_height)

                results.append(BoundaryResult(
                    coordinates=coordinates,
                    area=area,
                    perimeter=perimeter,
                    confidence=1.0,  # Grid is deterministic
                    method="grid",
                ))

        return results

    def visualize_boundaries(
        self,
        image: np.ndarray,
        boundaries: List[BoundaryResult],
        show_confidence: bool = True,
    ) -> np.ndarray:
        """
        Visualize detected boundaries on the image

        Args:
            image: Input image
            boundaries: List of boundaries to draw
            show_confidence: If True, display confidence scores

        Returns:
            Image with boundaries drawn
        """
        output = image.copy()

        for i, boundary in enumerate(boundaries):
            # Convert coordinates to numpy array
            points = np.array(boundary.coordinates, dtype=np.int32)
            points = points.reshape((-1, 1, 2))

            # Draw polygon
            color = (0, 255, 0)  # Green
            cv2.polylines(output, [points], isClosed=True, color=color, thickness=2)

            # Draw confidence if requested
            if show_confidence:
                # Get centroid
                M = cv2.moments(points)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])

                    # Draw confidence text
                    text = f"{boundary.confidence:.2f}"
                    cv2.putText(
                        output,
                        text,
                        (cx - 20, cy),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (255, 255, 255),
                        2,
                    )

        return output


# Helper function for easy usage
def detect_lot_boundaries(
    image_path: str,
    min_area: int = 1000,
    use_grid: bool = False,
    grid_rows: Optional[int] = None,
    grid_cols: Optional[int] = None,
) -> List[BoundaryResult]:
    """
    Convenience function to detect boundaries from an image file

    Args:
        image_path: Path to image file
        min_area: Minimum contour area
        use_grid: Use grid-based detection
        grid_rows: Number of grid rows
        grid_cols: Number of grid columns

    Returns:
        List of detected boundaries
    """
    # Read image
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not read image: {image_path}")

    # Create service
    service = BoundaryDetectionService(min_area=min_area)

    # Detect boundaries
    boundaries = service.detect_boundaries(
        image,
        use_grid=use_grid,
        grid_rows=grid_rows,
        grid_cols=grid_cols,
    )

    return boundaries
