"""
Barcode Generator
=================
Generates GS1-128 barcodes for SSCC and other identifiers.

Author: Integration Engineering Team
"""

from typing import Optional
from io import BytesIO
import logging

try:
    from barcode import Code128
    from barcode.writer import ImageWriter
    BARCODE_AVAILABLE = True
except ImportError:
    BARCODE_AVAILABLE = False
    logging.warning("python-barcode not installed, barcode generation will be limited")

from src.models.label_models import SSCC

logger = logging.getLogger(__name__)


class BarcodeGenerator:
    """
    Generates GS1-128 barcodes for shipping labels.

    GS1-128 uses Code 128 symbology with Application Identifiers (AI).
    For SSCC, the AI is (00).
    """

    def __init__(self):
        """Initialize barcode generator."""
        if not BARCODE_AVAILABLE:
            logger.warning("Barcode generation unavailable - install python-barcode")
        logger.info("Barcode generator initialized")

    def generate_sscc_barcode(
        self,
        sscc: SSCC,
        format: str = "PNG",
        height: int = 50,
        width: float = 0.2
    ) -> Optional[BytesIO]:
        """
        Generate GS1-128 barcode for SSCC.

        GS1-128 format for SSCC uses Application Identifier (00):
        Format: (00)18-digit-SSCC

        Args:
            sscc: SSCC object
            format: Output format (PNG, SVG)
            height: Barcode height in mm
            width: Module width (bar width)

        Returns:
            BytesIO object with barcode image, or None if generation fails

        Raises:
            ImportError: If python-barcode is not installed
        """
        if not BARCODE_AVAILABLE:
            raise ImportError("python-barcode library required for barcode generation")

        try:
            # GS1-128 format: (00) + 18-digit SSCC
            # Note: Code128 doesn't render the parentheses in the barcode itself
            # They're just for human readability
            barcode_data = sscc.get_full_sscc()

            logger.debug(f"Generating barcode for SSCC: {barcode_data}")

            # Create Code128 barcode
            writer = ImageWriter()
            writer.set_options({
                'module_height': height,
                'module_width': width,
                'quiet_zone': 6.5,  # Quiet zone in mm
                'font_size': 10,
                'text_distance': 5,
                'write_text': True
            })

            code128 = Code128(barcode_data, writer=writer)

            # Render to BytesIO
            output = BytesIO()
            code128.write(output, options={'format': format.upper()})
            output.seek(0)

            logger.debug(f"Barcode generated successfully: {len(output.getvalue())} bytes")
            return output

        except Exception as e:
            logger.error(f"Failed to generate barcode: {e}")
            raise

    def generate_barcode_from_string(
        self,
        data: str,
        format: str = "PNG",
        height: int = 50,
        width: float = 0.2,
        include_text: bool = True
    ) -> Optional[BytesIO]:
        """
        Generate Code 128 barcode from arbitrary string.

        Args:
            data: Data to encode
            format: Output format (PNG, SVG)
            height: Barcode height in mm
            width: Module width
            include_text: Whether to include human-readable text

        Returns:
            BytesIO object with barcode image

        Raises:
            ImportError: If python-barcode is not installed
        """
        if not BARCODE_AVAILABLE:
            raise ImportError("python-barcode library required for barcode generation")

        try:
            logger.debug(f"Generating barcode for: {data}")

            writer = ImageWriter()
            writer.set_options({
                'module_height': height,
                'module_width': width,
                'quiet_zone': 6.5,
                'font_size': 10 if include_text else 0,
                'text_distance': 5,
                'write_text': include_text
            })

            code128 = Code128(data, writer=writer)

            output = BytesIO()
            code128.write(output, options={'format': format.upper()})
            output.seek(0)

            return output

        except Exception as e:
            logger.error(f"Failed to generate barcode: {e}")
            raise

    def get_barcode_dimensions(
        self,
        sscc: SSCC,
        height: int = 50,
        width: float = 0.2
    ) -> tuple[float, float]:
        """
        Calculate barcode dimensions.

        Args:
            sscc: SSCC object
            height: Barcode height in mm
            width: Module width

        Returns:
            Tuple of (width_mm, height_mm)
        """
        # Code 128 has 11 bars per character + start/stop codes
        # SSCC is 18 digits
        num_chars = len(sscc.get_full_sscc())

        # Approximate width calculation
        # Code 128: each character is 11 modules wide
        # Plus start code (11 modules), stop code (13 modules), quiet zones
        total_modules = (num_chars * 11) + 11 + 13 + (2 * 10)  # Add quiet zones

        width_mm = total_modules * width
        height_mm = height

        return (width_mm, height_mm)


def create_barcode_generator() -> BarcodeGenerator:
    """
    Convenience function to create a barcode generator.

    Returns:
        BarcodeGenerator instance
    """
    return BarcodeGenerator()
