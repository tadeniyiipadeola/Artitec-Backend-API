"""
Few-Shot Learning Detector
Learns lot patterns from just 2-3 examples using template matching
Uses shape descriptors and similarity scoring
"""
import cv2
import numpy as np
import pickle
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from pathlib import Path
from scipy.spatial import distance


@dataclass
class LotPattern:
    """Stored lot pattern for few-shot learning"""
    name: str
    shape_descriptors: List[np.ndarray]  # Hu moments for each example
    contours: List[np.ndarray]  # Original contours
    avg_area: float
    area_std: float
    avg_vertices: float
    metadata: Optional[Dict] = None


@dataclass
class FewShotMatch:
    """Match result from few-shot detection"""
    coordinates: List[Tuple[int, int]]
    area: float
    confidence: float
    similarity_score: float
    matched_pattern: str


class FewShotDetector:
    """
    Few-shot learning detector for lot patterns

    Features:
    - Learn from 2-3 example lots
    - Shape descriptor matching (Hu moments)
    - Template matching
    - Contour similarity scoring
    - Pattern saving and loading
    - Multi-pattern support
    """

    def __init__(
        self,
        patterns_dir: Optional[str] = None,
        similarity_threshold: float = 0.7,
    ):
        """
        Initialize few-shot detector

        Args:
            patterns_dir: Directory to save/load patterns
            similarity_threshold: Minimum similarity score (0-1)
        """
        self.patterns_dir = Path(patterns_dir) if patterns_dir else None
        self.similarity_threshold = similarity_threshold
        self.patterns: Dict[str, LotPattern] = {}

        # Load existing patterns if directory exists
        if self.patterns_dir and self.patterns_dir.exists():
            self.load_all_patterns()

    def train_pattern(
        self,
        examples: List[np.ndarray],
        image: np.ndarray,
        pattern_name: str,
        save_pattern: bool = True,
    ) -> LotPattern:
        """
        Train a new lot pattern from example contours

        Args:
            examples: List of example contours (2-3 recommended)
            image: Source image
            pattern_name: Name for this pattern
            save_pattern: Save pattern to disk

        Returns:
            Trained lot pattern
        """
        if len(examples) < 2:
            raise ValueError("Need at least 2 examples for few-shot learning")

        # Extract shape descriptors from each example
        shape_descriptors = []
        areas = []
        vertex_counts = []

        for contour in examples:
            # Calculate Hu moments (shape descriptor)
            moments = cv2.moments(contour)
            hu_moments = cv2.HuMoments(moments).flatten()

            # Log transform for better scaling
            hu_moments = -np.sign(hu_moments) * np.log10(np.abs(hu_moments) + 1e-10)

            shape_descriptors.append(hu_moments)

            # Calculate area
            area = cv2.contourArea(contour)
            areas.append(area)

            # Count vertices
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            vertex_counts.append(len(approx))

        # Create pattern
        pattern = LotPattern(
            name=pattern_name,
            shape_descriptors=shape_descriptors,
            contours=examples,
            avg_area=float(np.mean(areas)),
            area_std=float(np.std(areas)),
            avg_vertices=float(np.mean(vertex_counts)),
            metadata={
                'training_samples': len(examples),
                'area_range': (float(np.min(areas)), float(np.max(areas))),
            }
        )

        # Store pattern
        self.patterns[pattern_name] = pattern

        # Save to disk
        if save_pattern and self.patterns_dir:
            self.save_pattern(pattern)

        return pattern

    def detect_similar_lots(
        self,
        image: np.ndarray,
        pattern_name: Optional[str] = None,
        min_area: int = 1000,
        max_area: Optional[int] = None,
    ) -> List[FewShotMatch]:
        """
        Detect lots similar to trained pattern

        Args:
            image: Input image
            pattern_name: Specific pattern to match (None = all patterns)
            min_area: Minimum lot area
            max_area: Maximum lot area

        Returns:
            List of matching lots
        """
        if not self.patterns:
            raise ValueError("No patterns loaded. Train a pattern first.")

        # Determine which patterns to use
        if pattern_name:
            if pattern_name not in self.patterns:
                raise ValueError(f"Pattern '{pattern_name}' not found")
            patterns = {pattern_name: self.patterns[pattern_name]}
        else:
            patterns = self.patterns

        # Find contours in image
        contours = self._find_contours(image, min_area, max_area)

        # Match contours against patterns
        matches = []

        for contour in contours:
            # Calculate shape descriptor for this contour
            contour_descriptor = self._extract_shape_descriptor(contour)
            contour_area = cv2.contourArea(contour)

            # Find best matching pattern
            best_match = None
            best_score = 0.0

            for pname, pattern in patterns.items():
                # Calculate similarity to each example in pattern
                similarities = []
                for pattern_descriptor in pattern.shape_descriptors:
                    sim = self._calculate_similarity(
                        contour_descriptor,
                        pattern_descriptor,
                    )
                    similarities.append(sim)

                # Use maximum similarity among examples
                max_similarity = max(similarities)

                # Check area similarity
                area_diff = abs(contour_area - pattern.avg_area)
                area_tolerance = 2 * pattern.area_std if pattern.area_std > 0 else pattern.avg_area * 0.5
                area_score = 1.0 - min(area_diff / area_tolerance, 1.0)

                # Combined score (shape 70%, area 30%)
                combined_score = max_similarity * 0.7 + area_score * 0.3

                if combined_score > best_score:
                    best_score = combined_score
                    best_match = pname

            # Add if above threshold
            if best_score >= self.similarity_threshold:
                # Get coordinates
                epsilon = 0.02 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                coordinates = [(int(p[0][0]), int(p[0][1])) for p in approx]

                matches.append(FewShotMatch(
                    coordinates=coordinates,
                    area=contour_area,
                    confidence=float(best_score),
                    similarity_score=float(best_score),
                    matched_pattern=best_match,
                ))

        # Sort by confidence
        matches.sort(key=lambda x: x.confidence, reverse=True)

        return matches

    def _find_contours(
        self,
        image: np.ndarray,
        min_area: int,
        max_area: Optional[int],
    ) -> List[np.ndarray]:
        """
        Find contours in image

        Args:
            image: Input image
            min_area: Minimum area
            max_area: Maximum area

        Returns:
            List of contours
        """
        # Preprocess
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Edge detection
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)

        # Morphological operations
        kernel = np.ones((3, 3), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=1)

        # Find contours
        contours, _ = cv2.findContours(
            dilated,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        # Filter by area
        filtered = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < min_area:
                continue
            if max_area and area > max_area:
                continue
            filtered.append(contour)

        return filtered

    def _extract_shape_descriptor(self, contour: np.ndarray) -> np.ndarray:
        """
        Extract shape descriptor (Hu moments) from contour

        Args:
            contour: OpenCV contour

        Returns:
            Shape descriptor vector
        """
        moments = cv2.moments(contour)
        hu_moments = cv2.HuMoments(moments).flatten()

        # Log transform
        hu_moments = -np.sign(hu_moments) * np.log10(np.abs(hu_moments) + 1e-10)

        return hu_moments

    def _calculate_similarity(
        self,
        descriptor1: np.ndarray,
        descriptor2: np.ndarray,
    ) -> float:
        """
        Calculate similarity between two shape descriptors

        Args:
            descriptor1: First descriptor
            descriptor2: Second descriptor

        Returns:
            Similarity score (0-1, higher is more similar)
        """
        # Euclidean distance
        dist = distance.euclidean(descriptor1, descriptor2)

        # Convert to similarity (inverse exponential)
        # Distance of 0 = similarity 1.0, larger distances approach 0
        similarity = np.exp(-dist / 10.0)

        return float(similarity)

    def save_pattern(self, pattern: LotPattern):
        """
        Save pattern to disk

        Args:
            pattern: Pattern to save
        """
        if not self.patterns_dir:
            raise ValueError("No patterns directory specified")

        self.patterns_dir.mkdir(parents=True, exist_ok=True)

        pattern_file = self.patterns_dir / f"{pattern.name}.pkl"

        with open(pattern_file, 'wb') as f:
            pickle.dump(pattern, f)

    def load_pattern(self, pattern_name: str) -> LotPattern:
        """
        Load pattern from disk

        Args:
            pattern_name: Name of pattern to load

        Returns:
            Loaded pattern
        """
        if not self.patterns_dir:
            raise ValueError("No patterns directory specified")

        pattern_file = self.patterns_dir / f"{pattern_name}.pkl"

        if not pattern_file.exists():
            raise FileNotFoundError(f"Pattern file not found: {pattern_file}")

        with open(pattern_file, 'rb') as f:
            pattern = pickle.load(f)

        self.patterns[pattern.name] = pattern

        return pattern

    def load_all_patterns(self):
        """Load all patterns from patterns directory"""
        if not self.patterns_dir or not self.patterns_dir.exists():
            return

        for pattern_file in self.patterns_dir.glob("*.pkl"):
            try:
                with open(pattern_file, 'rb') as f:
                    pattern = pickle.load(f)
                self.patterns[pattern.name] = pattern
            except Exception as e:
                print(f"Error loading pattern {pattern_file}: {e}")

    def delete_pattern(self, pattern_name: str):
        """
        Delete a pattern

        Args:
            pattern_name: Name of pattern to delete
        """
        # Remove from memory
        if pattern_name in self.patterns:
            del self.patterns[pattern_name]

        # Remove from disk
        if self.patterns_dir:
            pattern_file = self.patterns_dir / f"{pattern_name}.pkl"
            if pattern_file.exists():
                pattern_file.unlink()

    def list_patterns(self) -> List[str]:
        """
        List all available patterns

        Returns:
            List of pattern names
        """
        return list(self.patterns.keys())

    def get_pattern_info(self, pattern_name: str) -> Dict:
        """
        Get information about a pattern

        Args:
            pattern_name: Name of pattern

        Returns:
            Pattern information
        """
        if pattern_name not in self.patterns:
            raise ValueError(f"Pattern '{pattern_name}' not found")

        pattern = self.patterns[pattern_name]

        return {
            'name': pattern.name,
            'training_samples': len(pattern.shape_descriptors),
            'avg_area': pattern.avg_area,
            'area_std': pattern.area_std,
            'avg_vertices': pattern.avg_vertices,
            'metadata': pattern.metadata,
        }

    def visualize_matches(
        self,
        image: np.ndarray,
        matches: List[FewShotMatch],
        show_pattern_names: bool = True,
        show_confidence: bool = True,
    ) -> np.ndarray:
        """
        Visualize few-shot detection matches

        Args:
            image: Input image
            matches: Detection matches
            show_pattern_names: Show matched pattern names
            show_confidence: Show confidence scores

        Returns:
            Image with visualizations
        """
        output = image.copy()

        # Color map for different patterns
        pattern_colors = {}
        colors = [
            (0, 255, 0),    # Green
            (255, 0, 0),    # Blue
            (0, 0, 255),    # Red
            (255, 255, 0),  # Cyan
            (255, 0, 255),  # Magenta
            (0, 255, 255),  # Yellow
        ]

        for match in matches:
            # Assign color based on pattern
            if match.matched_pattern not in pattern_colors:
                color_idx = len(pattern_colors) % len(colors)
                pattern_colors[match.matched_pattern] = colors[color_idx]

            color = pattern_colors[match.matched_pattern]

            # Draw polygon
            points = np.array(match.coordinates, dtype=np.int32)
            points = points.reshape((-1, 1, 2))
            cv2.polylines(output, [points], isClosed=True, color=color, thickness=2)

            # Calculate centroid for text
            M = cv2.moments(points)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])

                # Prepare text
                texts = []
                if show_pattern_names:
                    texts.append(match.matched_pattern)
                if show_confidence:
                    texts.append(f"{match.confidence:.2f}")

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


# Helper functions
def train_pattern_from_coordinates(
    coordinates_list: List[List[Tuple[int, int]]],
    image: np.ndarray,
    pattern_name: str,
    patterns_dir: Optional[str] = None,
) -> LotPattern:
    """
    Train pattern from coordinate lists

    Args:
        coordinates_list: List of polygon coordinate lists
        image: Source image
        pattern_name: Pattern name
        patterns_dir: Directory to save pattern

    Returns:
        Trained pattern
    """
    # Convert coordinates to contours
    contours = []
    for coords in coordinates_list:
        points = np.array(coords, dtype=np.int32)
        contours.append(points)

    detector = FewShotDetector(patterns_dir=patterns_dir)
    pattern = detector.train_pattern(contours, image, pattern_name)

    return pattern
