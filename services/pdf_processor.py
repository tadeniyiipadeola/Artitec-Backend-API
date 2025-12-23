"""
PDF Processor Service
Converts PDF site plans to images for lot detection
Supports multi-page PDFs and quality settings
"""
import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from pathlib import Path
import tempfile


@dataclass
class PDFPage:
    """Represents a converted PDF page"""
    page_number: int
    image: np.ndarray
    width: int
    height: int
    dpi: int


@dataclass
class PDFProcessResult:
    """Result of PDF processing"""
    total_pages: int
    pages: List[PDFPage]
    metadata: Dict


class PDFProcessor:
    """
    PDF processor for site plan documents

    Features:
    - Convert PDF pages to images
    - Adjustable DPI/resolution
    - Multi-page support
    - Metadata extraction
    - Image enhancement options
    """

    def __init__(
        self,
        dpi: int = 300,
        enhance_images: bool = True,
    ):
        """
        Initialize PDF processor

        Args:
            dpi: Resolution for PDF conversion (default 300 DPI)
            enhance_images: Apply image enhancement after conversion
        """
        self.dpi = dpi
        self.enhance_images = enhance_images

        # Check if PyMuPDF is available
        try:
            import fitz  # PyMuPDF
            self.fitz = fitz
            self.pdf_support = True
        except ImportError:
            self.fitz = None
            self.pdf_support = False
            print("Warning: PyMuPDF not installed. PDF processing unavailable.")

    def process_pdf(
        self,
        pdf_path: str,
        page_numbers: Optional[List[int]] = None,
    ) -> PDFProcessResult:
        """
        Process PDF and convert to images

        Args:
            pdf_path: Path to PDF file
            page_numbers: Specific page numbers to process (None = all pages)

        Returns:
            PDF processing result with converted pages
        """
        if not self.pdf_support:
            raise RuntimeError("PyMuPDF not installed. Install with: pip install PyMuPDF")

        # Open PDF
        doc = self.fitz.open(pdf_path)

        # Get metadata
        metadata = {
            'title': doc.metadata.get('title', ''),
            'author': doc.metadata.get('author', ''),
            'subject': doc.metadata.get('subject', ''),
            'total_pages': len(doc),
            'format': doc.metadata.get('format', ''),
        }

        # Determine which pages to process
        if page_numbers is None:
            page_numbers = list(range(len(doc)))
        else:
            # Validate page numbers
            page_numbers = [p for p in page_numbers if 0 <= p < len(doc)]

        # Convert pages
        pages = []
        for page_num in page_numbers:
            page_image = self._convert_page(doc, page_num)

            pages.append(PDFPage(
                page_number=page_num + 1,  # 1-indexed for user display
                image=page_image,
                width=page_image.shape[1],
                height=page_image.shape[0],
                dpi=self.dpi,
            ))

        doc.close()

        return PDFProcessResult(
            total_pages=len(doc),
            pages=pages,
            metadata=metadata,
        )

    def _convert_page(
        self,
        doc,
        page_num: int,
    ) -> np.ndarray:
        """
        Convert single PDF page to image

        Args:
            doc: PyMuPDF document
            page_num: Page number (0-indexed)

        Returns:
            OpenCV image (numpy array)
        """
        # Load page
        page = doc.load_page(page_num)

        # Calculate zoom factor for desired DPI
        # PDF default is 72 DPI
        zoom = self.dpi / 72

        # Render page to pixmap
        mat = self.fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)

        # Convert to numpy array
        img_data = pix.samples
        img = np.frombuffer(img_data, dtype=np.uint8)
        img = img.reshape(pix.height, pix.width, pix.n)

        # Convert RGB to BGR for OpenCV
        if pix.n == 3:  # RGB
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        elif pix.n == 4:  # RGBA
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)

        # Apply enhancement if enabled
        if self.enhance_images:
            img = self._enhance_image(img)

        return img

    def _enhance_image(self, image: np.ndarray) -> np.ndarray:
        """
        Enhance converted PDF image for better detection

        Args:
            image: Input image

        Returns:
            Enhanced image
        """
        # Convert to grayscale for processing
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # Denoise
        denoised = cv2.fastNlMeansDenoising(enhanced, None, h=10)

        # Convert back to BGR if original was color
        if len(image.shape) == 3:
            enhanced_bgr = cv2.cvtColor(denoised, cv2.COLOR_GRAY2BGR)
            return enhanced_bgr
        else:
            return denoised

    def save_pages_as_images(
        self,
        pdf_path: str,
        output_dir: str,
        prefix: str = "page",
        format: str = "png",
    ) -> List[str]:
        """
        Convert PDF pages and save as individual images

        Args:
            pdf_path: Path to PDF file
            output_dir: Output directory for images
            prefix: Filename prefix
            format: Image format (png, jpg, tiff)

        Returns:
            List of saved image paths
        """
        result = self.process_pdf(pdf_path)

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Save pages
        saved_paths = []
        for page in result.pages:
            filename = f"{prefix}_{page.page_number:03d}.{format}"
            filepath = output_path / filename

            cv2.imwrite(str(filepath), page.image)
            saved_paths.append(str(filepath))

        return saved_paths

    def extract_specific_page(
        self,
        pdf_path: str,
        page_number: int,
    ) -> np.ndarray:
        """
        Extract a specific page as image

        Args:
            pdf_path: Path to PDF file
            page_number: Page number (1-indexed)

        Returns:
            Page image
        """
        result = self.process_pdf(pdf_path, page_numbers=[page_number - 1])

        if not result.pages:
            raise ValueError(f"Page {page_number} not found in PDF")

        return result.pages[0].image

    def get_pdf_info(self, pdf_path: str) -> Dict:
        """
        Get PDF metadata and information

        Args:
            pdf_path: Path to PDF file

        Returns:
            PDF information dictionary
        """
        if not self.pdf_support:
            raise RuntimeError("PyMuPDF not installed")

        doc = self.fitz.open(pdf_path)

        info = {
            'filename': Path(pdf_path).name,
            'total_pages': len(doc),
            'metadata': {
                'title': doc.metadata.get('title', ''),
                'author': doc.metadata.get('author', ''),
                'subject': doc.metadata.get('subject', ''),
                'keywords': doc.metadata.get('keywords', ''),
                'creator': doc.metadata.get('creator', ''),
                'producer': doc.metadata.get('producer', ''),
                'format': doc.metadata.get('format', ''),
            },
            'pages': [],
        }

        # Get page dimensions
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            rect = page.rect

            info['pages'].append({
                'page_number': page_num + 1,
                'width': rect.width,
                'height': rect.height,
                'rotation': page.rotation,
            })

        doc.close()

        return info


# Convenience functions

def pdf_to_images(
    pdf_path: str,
    dpi: int = 300,
    output_dir: Optional[str] = None,
) -> List[np.ndarray]:
    """
    Convert PDF to list of images

    Args:
        pdf_path: Path to PDF file
        dpi: Resolution
        output_dir: If provided, save images to this directory

    Returns:
        List of page images
    """
    processor = PDFProcessor(dpi=dpi)
    result = processor.process_pdf(pdf_path)

    # Save if output directory provided
    if output_dir:
        processor.save_pages_as_images(
            pdf_path,
            output_dir,
            prefix=Path(pdf_path).stem,
        )

    return [page.image for page in result.pages]


def process_pdf_for_detection(
    pdf_path: str,
    page_number: Optional[int] = None,
    dpi: int = 300,
) -> np.ndarray:
    """
    Process PDF for lot detection

    Args:
        pdf_path: Path to PDF file
        page_number: Specific page to process (1-indexed), None = first page
        dpi: Resolution

    Returns:
        Processed image ready for detection
    """
    processor = PDFProcessor(dpi=dpi, enhance_images=True)

    if page_number is None:
        # Use first page
        result = processor.process_pdf(pdf_path, page_numbers=[0])
        return result.pages[0].image
    else:
        return processor.extract_specific_page(pdf_path, page_number)


def batch_convert_pdfs(
    pdf_paths: List[str],
    output_dir: str,
    dpi: int = 300,
) -> Dict[str, List[str]]:
    """
    Batch convert multiple PDFs to images

    Args:
        pdf_paths: List of PDF file paths
        output_dir: Output directory
        dpi: Resolution

    Returns:
        Dictionary mapping PDF paths to lists of output image paths
    """
    processor = PDFProcessor(dpi=dpi)

    results = {}
    for pdf_path in pdf_paths:
        pdf_name = Path(pdf_path).stem

        # Create subdirectory for each PDF
        pdf_output_dir = Path(output_dir) / pdf_name

        saved_paths = processor.save_pages_as_images(
            pdf_path,
            str(pdf_output_dir),
            prefix="page",
        )

        results[pdf_path] = saved_paths

    return results


# PDF validation
def is_valid_pdf(file_path: str) -> bool:
    """
    Check if file is a valid PDF

    Args:
        file_path: Path to file

    Returns:
        True if valid PDF
    """
    try:
        import fitz
        doc = fitz.open(file_path)
        is_valid = len(doc) > 0
        doc.close()
        return is_valid
    except:
        return False


def get_pdf_page_count(file_path: str) -> int:
    """
    Get number of pages in PDF

    Args:
        file_path: Path to PDF file

    Returns:
        Number of pages
    """
    try:
        import fitz
        doc = fitz.open(file_path)
        count = len(doc)
        doc.close()
        return count
    except:
        return 0
