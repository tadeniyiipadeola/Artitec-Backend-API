"""
Line-based Lot Detector Service
Detects lot boundaries using Hough line detection and polygon formation
Fallback method when YOLO or ML models are unavailable
"""
import cv2
import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass
from scipy.spatial import distance


@dataclass
class LineSegment:
    """Represents a detected line segment"""
    x1: int
    y1: int
    x2: int
    y2: int
    angle: float
    length: float


@dataclass
class LotPolygon:
    """Represents a detected lot polygon"""
    vertices: List[Tuple[int, int]]
    area: float
    confidence: float
    method: str = "line_detection"


class LineLotDetector:
    """
    Detect lot boundaries using line detection

    Features:
    - Hough Line Transform for line detection
    - Line intersection calculation
    - Polygon formation from intersecting lines
    - Filtering for 4-8 sided polygons
    - Text region filtering to avoid lot numbers
    """

    def __init__(
        self,
        min_line_length: int = 50,
        max_line_gap: int = 10,
        angle_threshold: float = 10.0,
        min_polygon_area: int = 1000,
        max_polygon_area: Optional[int] = None,
    ):
        """
        Initialize line-based lot detector

        Args:
            min_line_length: Minimum line length to detect
            max_line_gap: Maximum gap between line segments
            angle_threshold: Angle difference threshold for parallel lines (degrees)
            min_polygon_area: Minimum polygon area
            max_polygon_area: Maximum polygon area
        """
        self.min_line_length = min_line_length
        self.max_line_gap = max_line_gap
        self.angle_threshold = angle_threshold
        self.min_polygon_area = min_polygon_area
        self.max_polygon_area = max_polygon_area

    def detect_lots(self, image: np.ndarray) -> List[LotPolygon]:
        """
        Detect lot polygons from image

        Args:
            image: Input image (BGR or grayscale)

        Returns:
            List of detected lot polygons
        """
        # Detect lines
        lines = self._detect_lines(image)

        if not lines:
            return []

        # Find line intersections
        intersections = self._find_intersections(lines)

        # Form polygons from intersections
        polygons = self._form_polygons(intersections, lines)

        # Filter and validate polygons
        valid_polygons = self._filter_polygons(polygons, image)

        return valid_polygons

    def _detect_lines(self, image: np.ndarray) -> List[LineSegment]:
        """
        Detect lines using Hough Line Transform

        Args:
            image: Input image

        Returns:
            List of detected line segments
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Edge detection
        edges = cv2.Canny(blurred, 50, 150, apertureSize=3)

        # Hough Line Transform (Probabilistic)
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=80,
            minLineLength=self.min_line_length,
            maxLineGap=self.max_line_gap,
        )

        if lines is None:
            return []

        # Convert to LineSegment objects
        line_segments = []
        for line in lines:
            x1, y1, x2, y2 = line[0]

            # Calculate angle and length
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

            line_segments.append(LineSegment(
                x1=int(x1),
                y1=int(y1),
                x2=int(x2),
                y2=int(y2),
                angle=angle,
                length=length,
            ))

        # Merge collinear lines
        line_segments = self._merge_collinear_lines(line_segments)

        return line_segments

    def _merge_collinear_lines(
        self,
        lines: List[LineSegment],
    ) -> List[LineSegment]:
        """
        Merge collinear or nearly collinear line segments

        Args:
            lines: List of line segments

        Returns:
            List of merged line segments
        """
        if not lines:
            return []

        merged = []
        used = set()

        for i, line1 in enumerate(lines):
            if i in used:
                continue

            # Find lines with similar angles
            similar_lines = [line1]
            for j, line2 in enumerate(lines):
                if j <= i or j in used:
                    continue

                # Check if angles are similar
                angle_diff = abs(line1.angle - line2.angle)
                if angle_diff > 180:
                    angle_diff = 360 - angle_diff

                if angle_diff < self.angle_threshold:
                    # Check if lines are close to each other
                    # Simplified check: if endpoints are close
                    dist = min(
                        distance.euclidean((line1.x1, line1.y1), (line2.x1, line2.y1)),
                        distance.euclidean((line1.x1, line1.y1), (line2.x2, line2.y2)),
                        distance.euclidean((line1.x2, line1.y2), (line2.x1, line2.y1)),
                        distance.euclidean((line1.x2, line1.y2), (line2.x2, line2.y2)),
                    )

                    if dist < self.max_line_gap * 2:
                        similar_lines.append(line2)
                        used.add(j)

            # Merge similar lines by finding extreme points
            if len(similar_lines) > 1:
                all_points = []
                for line in similar_lines:
                    all_points.extend([(line.x1, line.y1), (line.x2, line.y2)])

                # Find extreme points along the average angle
                avg_angle = np.mean([line.angle for line in similar_lines])
                projection_axis = np.array([np.cos(np.radians(avg_angle)), np.sin(np.radians(avg_angle))])

                projections = [np.dot(point, projection_axis) for point in all_points]
                min_idx = np.argmin(projections)
                max_idx = np.argmax(projections)

                x1, y1 = all_points[min_idx]
                x2, y2 = all_points[max_idx]

                length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

                merged.append(LineSegment(
                    x1=int(x1),
                    y1=int(y1),
                    x2=int(x2),
                    y2=int(y2),
                    angle=avg_angle,
                    length=length,
                ))
            else:
                merged.append(line1)

            used.add(i)

        return merged

    def _find_intersections(
        self,
        lines: List[LineSegment],
    ) -> List[Tuple[int, int]]:
        """
        Find intersection points between lines

        Args:
            lines: List of line segments

        Returns:
            List of intersection points
        """
        intersections = []

        for i, line1 in enumerate(lines):
            for j, line2 in enumerate(lines):
                if j <= i:
                    continue

                # Calculate intersection
                intersection = self._line_intersection(line1, line2)
                if intersection:
                    intersections.append(intersection)

        # Remove duplicates (points close to each other)
        unique_intersections = []
        for point in intersections:
            is_duplicate = False
            for existing in unique_intersections:
                if distance.euclidean(point, existing) < 10:  # 10 pixel threshold
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_intersections.append(point)

        return unique_intersections

    def _line_intersection(
        self,
        line1: LineSegment,
        line2: LineSegment,
    ) -> Optional[Tuple[int, int]]:
        """
        Calculate intersection point of two line segments

        Args:
            line1: First line segment
            line2: Second line segment

        Returns:
            Intersection point or None
        """
        x1, y1, x2, y2 = line1.x1, line1.y1, line1.x2, line1.y2
        x3, y3, x4, y4 = line2.x1, line2.y1, line2.x2, line2.y2

        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)

        if abs(denom) < 1e-10:  # Lines are parallel
            return None

        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom

        # Check if intersection is within line segments (with some tolerance)
        if -0.1 <= t <= 1.1 and -0.1 <= u <= 1.1:
            x = int(x1 + t * (x2 - x1))
            y = int(y1 + t * (y2 - y1))
            return (x, y)

        return None

    def _form_polygons(
        self,
        intersections: List[Tuple[int, int]],
        lines: List[LineSegment],
    ) -> List[LotPolygon]:
        """
        Form polygons from intersection points

        Args:
            intersections: List of intersection points
            lines: Original line segments

        Returns:
            List of polygons
        """
        # This is a simplified approach
        # In a production system, you'd use graph algorithms to find cycles

        polygons = []

        # For now, use convex hull of nearby points as a simple approach
        if len(intersections) < 4:
            return []

        # Group intersections into clusters (potential polygons)
        from sklearn.cluster import DBSCAN

        if len(intersections) < 4:
            return []

        points = np.array(intersections)
        clustering = DBSCAN(eps=100, min_samples=4).fit(points)

        for cluster_id in set(clustering.labels_):
            if cluster_id == -1:  # Noise
                continue

            cluster_points = points[clustering.labels_ == cluster_id]

            if len(cluster_points) < 4:
                continue

            # Calculate convex hull
            hull = cv2.convexHull(cluster_points.astype(np.float32))
            vertices = [(int(point[0][0]), int(point[0][1])) for point in hull]

            # Calculate area
            area = cv2.contourArea(hull)

            if area < self.min_polygon_area:
                continue

            if self.max_polygon_area and area > self.max_polygon_area:
                continue

            polygons.append(LotPolygon(
                vertices=vertices,
                area=area,
                confidence=0.7,  # Line detection is less confident than ML
            ))

        return polygons

    def _filter_polygons(
        self,
        polygons: List[LotPolygon],
        image: np.ndarray,
    ) -> List[LotPolygon]:
        """
        Filter and validate detected polygons

        Args:
            polygons: List of detected polygons
            image: Original image

        Returns:
            Filtered list of polygons
        """
        valid = []

        for polygon in polygons:
            # Filter by vertex count (4-8 sided)
            if len(polygon.vertices) < 4 or len(polygon.vertices) > 8:
                continue

            # Filter by area
            if polygon.area < self.min_polygon_area:
                continue

            if self.max_polygon_area and polygon.area > self.max_polygon_area:
                continue

            # Check if polygon contains mostly text (lot numbers)
            # Skip this for now - would need OCR integration

            valid.append(polygon)

        # Sort by area (larger lots first)
        valid.sort(key=lambda x: x.area, reverse=True)

        return valid


# Helper function
def detect_lots_from_image(
    image_path: str,
    min_area: int = 1000,
) -> List[LotPolygon]:
    """
    Convenience function to detect lots from image file

    Args:
        image_path: Path to image
        min_area: Minimum lot area

    Returns:
        List of detected lots
    """
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not read image: {image_path}")

    detector = LineLotDetector(min_polygon_area=min_area)
    lots = detector.detect_lots(image)

    return lots
