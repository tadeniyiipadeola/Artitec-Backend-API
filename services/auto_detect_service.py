"""
Auto-Detect Service
Combines OCR, boundary detection, and line detection for comprehensive lot detection
Automatically matches lot numbers to detected boundaries
"""
import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from scipy.spatial import distance

from services.ocr_service import OCRService, LotNumberResult
from services.boundary_detection import BoundaryDetectionService, BoundaryResult
from services.line_lot_detector import LineLotDetector, LotPolygon


@dataclass
class DetectedLot:
    """Complete lot detection result with boundary and lot number"""
    lot_number: Optional[str]
    coordinates: List[Tuple[int, int]]  # Polygon vertices
    area: float
    confidence: float
    detection_method: str  # "boundary+ocr", "line+ocr", "boundary_only", "grid"
    ocr_confidence: Optional[float] = None
    boundary_confidence: Optional[float] = None


class AutoDetectService:
    """
    Automatic lot detection combining multiple detection methods

    Features:
    - Boundary detection for lot polygons
    - OCR for lot number extraction
    - Spatial matching of lot numbers to boundaries
    - Fallback detection strategies
    - Grid-based detection option
    - Confidence scoring and ranking
    """

    def __init__(
        self,
        min_area: int = 1000,
        max_area: Optional[int] = None,
        ocr_min_confidence: float = 60.0,
        matching_max_distance: int = 100,
        use_line_fallback: bool = True,
    ):
        """
        Initialize auto-detect service

        Args:
            min_area: Minimum lot area in pixels
            max_area: Maximum lot area in pixels
            ocr_min_confidence: Minimum OCR confidence score
            matching_max_distance: Maximum distance to match lot number to boundary
            use_line_fallback: Use line detection if boundary detection fails
        """
        self.min_area = min_area
        self.max_area = max_area
        self.matching_max_distance = matching_max_distance
        self.use_line_fallback = use_line_fallback

        # Initialize detection services
        self.ocr_service = OCRService(min_confidence=ocr_min_confidence)
        self.boundary_service = BoundaryDetectionService(
            min_area=min_area,
            max_area=max_area,
        )
        self.line_detector = LineLotDetector(
            min_polygon_area=min_area,
            max_polygon_area=max_area,
        )

    def detect_lots(
        self,
        image: np.ndarray,
        use_ocr: bool = True,
        use_grid: bool = False,
        grid_rows: Optional[int] = None,
        grid_cols: Optional[int] = None,
    ) -> List[DetectedLot]:
        """
        Automatically detect lots in image

        Args:
            image: Input image (BGR or grayscale)
            use_ocr: Extract lot numbers using OCR
            use_grid: Use grid-based detection
            grid_rows: Number of grid rows
            grid_cols: Number of grid columns

        Returns:
            List of detected lots with boundaries and lot numbers
        """
        # Step 1: Detect boundaries
        if use_grid and grid_rows and grid_cols:
            boundaries = self.boundary_service.detect_boundaries(
                image,
                use_grid=True,
                grid_rows=grid_rows,
                grid_cols=grid_cols,
            )
            method = "grid"
        else:
            # Try boundary detection first
            boundaries = self.boundary_service.detect_boundaries(image, use_grid=False)

            # Fallback to line detection if boundary detection fails
            if not boundaries and self.use_line_fallback:
                line_polygons = self.line_detector.detect_lots(image)
                # Convert LotPolygon to BoundaryResult
                boundaries = [
                    BoundaryResult(
                        coordinates=poly.vertices,
                        area=poly.area,
                        perimeter=self._calculate_perimeter(poly.vertices),
                        confidence=poly.confidence,
                        method="line_detection",
                    )
                    for poly in line_polygons
                ]

            method = boundaries[0].method if boundaries else "edge_detection"

        if not boundaries:
            return []

        # Step 2: Extract lot numbers using OCR (if enabled)
        lot_numbers = []
        if use_ocr:
            lot_numbers = self.ocr_service.extract_lot_numbers(image)

        # Step 3: Match lot numbers to boundaries
        detected_lots = self._match_lots_to_boundaries(
            boundaries,
            lot_numbers,
            method,
        )

        # Step 4: Sort by confidence
        detected_lots.sort(key=lambda x: x.confidence, reverse=True)

        return detected_lots

    def _match_lots_to_boundaries(
        self,
        boundaries: List[BoundaryResult],
        lot_numbers: List[LotNumberResult],
        method: str,
    ) -> List[DetectedLot]:
        """
        Match detected lot numbers to detected boundaries

        Args:
            boundaries: Detected boundary polygons
            lot_numbers: Detected lot numbers from OCR
            method: Detection method used

        Returns:
            List of matched lots
        """
        detected_lots = []

        # Track which lot numbers have been used
        used_lot_numbers = set()

        for boundary in boundaries:
            # Calculate polygon centroid
            centroid = self._calculate_centroid(boundary.coordinates)

            # Find closest lot number to this boundary
            best_match = None
            best_distance = float('inf')

            for i, lot_num in enumerate(lot_numbers):
                if i in used_lot_numbers:
                    continue

                # Check if lot number is inside or near polygon
                dist = distance.euclidean(centroid, lot_num.position)

                # Also check if point is inside polygon
                is_inside = self._point_in_polygon(
                    lot_num.position,
                    boundary.coordinates,
                )

                # Prefer inside matches, otherwise use distance
                if is_inside:
                    dist *= 0.1  # Strong preference for inside matches

                if dist < best_distance and dist < self.matching_max_distance:
                    best_distance = dist
                    best_match = (i, lot_num, dist)

            # Create detected lot
            if best_match:
                idx, lot_num, dist = best_match
                used_lot_numbers.add(idx)

                # Calculate combined confidence
                # Higher weight to boundary confidence, OCR confidence as bonus
                combined_confidence = (
                    boundary.confidence * 0.7 +
                    (lot_num.confidence / 100.0) * 0.3
                )

                detected_lots.append(DetectedLot(
                    lot_number=lot_num.lot_number,
                    coordinates=boundary.coordinates,
                    area=boundary.area,
                    confidence=combined_confidence,
                    detection_method=f"{method}+ocr",
                    ocr_confidence=lot_num.confidence,
                    boundary_confidence=boundary.confidence,
                ))
            else:
                # No matching lot number found
                detected_lots.append(DetectedLot(
                    lot_number=None,
                    coordinates=boundary.coordinates,
                    area=boundary.area,
                    confidence=boundary.confidence * 0.8,  # Lower confidence without OCR
                    detection_method=method,
                    ocr_confidence=None,
                    boundary_confidence=boundary.confidence,
                ))

        return detected_lots

    def _calculate_centroid(
        self,
        coordinates: List[Tuple[int, int]],
    ) -> Tuple[float, float]:
        """
        Calculate centroid of polygon

        Args:
            coordinates: Polygon vertices

        Returns:
            Centroid (x, y)
        """
        if not coordinates:
            return (0.0, 0.0)

        x_coords = [p[0] for p in coordinates]
        y_coords = [p[1] for p in coordinates]

        centroid_x = sum(x_coords) / len(x_coords)
        centroid_y = sum(y_coords) / len(y_coords)

        return (centroid_x, centroid_y)

    def _calculate_perimeter(
        self,
        coordinates: List[Tuple[int, int]],
    ) -> float:
        """
        Calculate perimeter of polygon

        Args:
            coordinates: Polygon vertices

        Returns:
            Perimeter length
        """
        if len(coordinates) < 2:
            return 0.0

        perimeter = 0.0
        for i in range(len(coordinates)):
            p1 = coordinates[i]
            p2 = coordinates[(i + 1) % len(coordinates)]
            perimeter += distance.euclidean(p1, p2)

        return perimeter

    def _point_in_polygon(
        self,
        point: Tuple[int, int],
        polygon: List[Tuple[int, int]],
    ) -> bool:
        """
        Check if point is inside polygon using ray casting algorithm

        Args:
            point: Point (x, y)
            polygon: Polygon vertices

        Returns:
            True if point is inside polygon
        """
        x, y = point
        n = len(polygon)
        inside = False

        p1x, p1y = polygon[0]
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y

        return inside

    def visualize_results(
        self,
        image: np.ndarray,
        lots: List[DetectedLot],
        show_confidence: bool = True,
        show_method: bool = False,
    ) -> np.ndarray:
        """
        Visualize detected lots on image

        Args:
            image: Input image
            lots: Detected lots
            show_confidence: Show confidence scores
            show_method: Show detection method

        Returns:
            Image with visualizations
        """
        output = image.copy()

        for lot in lots:
            # Convert coordinates to numpy array
            points = np.array(lot.coordinates, dtype=np.int32)
            points = points.reshape((-1, 1, 2))

            # Color based on confidence
            if lot.confidence > 0.8:
                color = (0, 255, 0)  # Green - high confidence
            elif lot.confidence > 0.6:
                color = (0, 255, 255)  # Yellow - medium confidence
            else:
                color = (0, 165, 255)  # Orange - low confidence

            # Draw polygon
            cv2.polylines(output, [points], isClosed=True, color=color, thickness=2)

            # Fill polygon with semi-transparent color
            overlay = output.copy()
            cv2.fillPoly(overlay, [points], color)
            cv2.addWeighted(overlay, 0.1, output, 0.9, 0, output)

            # Calculate centroid for text placement
            centroid = self._calculate_centroid(lot.coordinates)
            cx, cy = int(centroid[0]), int(centroid[1])

            # Prepare text
            texts = []
            if lot.lot_number:
                texts.append(lot.lot_number)
            if show_confidence:
                texts.append(f"{lot.confidence:.2f}")
            if show_method:
                texts.append(lot.detection_method)

            # Draw text
            y_offset = 0
            for text in texts:
                cv2.putText(
                    output,
                    text,
                    (cx - 30, cy + y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 255),
                    2,
                )
                y_offset += 20

        return output

    def get_statistics(self, lots: List[DetectedLot]) -> Dict:
        """
        Get statistics about detected lots

        Args:
            lots: Detected lots

        Returns:
            Statistics dictionary
        """
        total = len(lots)
        with_lot_numbers = sum(1 for lot in lots if lot.lot_number)
        without_lot_numbers = total - with_lot_numbers

        # Confidence distribution
        high_conf = sum(1 for lot in lots if lot.confidence > 0.8)
        medium_conf = sum(1 for lot in lots if 0.6 < lot.confidence <= 0.8)
        low_conf = sum(1 for lot in lots if lot.confidence <= 0.6)

        # Detection methods
        methods = {}
        for lot in lots:
            method = lot.detection_method
            methods[method] = methods.get(method, 0) + 1

        # Area statistics
        areas = [lot.area for lot in lots]
        avg_area = sum(areas) / len(areas) if areas else 0
        min_area = min(areas) if areas else 0
        max_area = max(areas) if areas else 0

        return {
            "total_lots": total,
            "with_lot_numbers": with_lot_numbers,
            "without_lot_numbers": without_lot_numbers,
            "confidence_distribution": {
                "high": high_conf,
                "medium": medium_conf,
                "low": low_conf,
            },
            "detection_methods": methods,
            "area_statistics": {
                "average": avg_area,
                "minimum": min_area,
                "maximum": max_area,
            },
        }


# Helper function for easy usage
def auto_detect_lots(
    image_path: str,
    use_ocr: bool = True,
    use_grid: bool = False,
    grid_rows: Optional[int] = None,
    grid_cols: Optional[int] = None,
    min_area: int = 1000,
) -> List[DetectedLot]:
    """
    Convenience function to auto-detect lots from image file

    Args:
        image_path: Path to image
        use_ocr: Use OCR to extract lot numbers
        use_grid: Use grid-based detection
        grid_rows: Number of grid rows
        grid_cols: Number of grid columns
        min_area: Minimum lot area

    Returns:
        List of detected lots
    """
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not read image: {image_path}")

    service = AutoDetectService(min_area=min_area)
    lots = service.detect_lots(
        image,
        use_ocr=use_ocr,
        use_grid=use_grid,
        grid_rows=grid_rows,
        grid_cols=grid_cols,
    )

    return lots
