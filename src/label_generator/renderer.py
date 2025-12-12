"""
Label Renderer
==============
Renders shipping labels as PDF using reportlab.

Supports standard 4x6 inch shipping label format with:
- SSCC barcode
- Ship-from/ship-to addresses
- Carton information
- Weight and contents

Author: Integration Engineering Team
"""

from typing import Optional, List
from pathlib import Path
from io import BytesIO
import logging

try:
    from reportlab.lib.pagesizes import inch
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logging.warning("reportlab not installed, PDF generation will be limited")

from src.models.label_models import ShippingLabel, LabelConfig, LabelSize
from src.label_generator.barcode import BarcodeGenerator

logger = logging.getLogger(__name__)


class LabelRenderer:
    """
    Renders shipping labels as PDF documents.

    Supports standard label sizes (4x6, 4x8, etc.) and includes:
    - GS1-128 SSCC barcode
    - Ship-from and ship-to addresses
    - Carton sequence information
    - Weight and item count
    - Optional contents list
    """

    def __init__(self, config: Optional[LabelConfig] = None):
        """
        Initialize label renderer.

        Args:
            config: Label configuration (uses defaults if not provided)

        Raises:
            ImportError: If reportlab is not installed
        """
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab library required for label rendering")

        self.config = config or LabelConfig()
        self.barcode_gen = BarcodeGenerator()

        logger.info(f"Label renderer initialized: {self.config.label_size.value}")

    def render_label(
        self,
        label: ShippingLabel,
        output_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Render a single shipping label.

        Args:
            label: ShippingLabel data
            output_path: Path to save PDF (if None, returns BytesIO)

        Returns:
            Path to saved file, or None if returning BytesIO

        Raises:
            ValueError: If label data is invalid
        """
        logger.info(f"Rendering label for carton {label.carton_sequence}/{label.total_cartons}")

        # Get page dimensions
        width, height = self._get_page_dimensions()

        # Create canvas
        if output_path:
            c = canvas.Canvas(output_path, pagesize=(width, height))
        else:
            buffer = BytesIO()
            c = canvas.Canvas(buffer, pagesize=(width, height))

        try:
            # Render label content
            self._render_label_content(c, label, width, height)

            # Save PDF
            c.save()

            if output_path:
                logger.info(f"Label saved to: {output_path}")
                return output_path
            else:
                buffer.seek(0)
                return buffer

        except Exception as e:
            logger.error(f"Failed to render label: {e}")
            raise

    def _render_label_content(
        self,
        c: canvas.Canvas,
        label: ShippingLabel,
        width: float,
        height: float
    ):
        """
        Render the actual label content on the canvas.

        Args:
            c: ReportLab canvas
            label: ShippingLabel data
            width: Page width in points
            height: Page height in points
        """
        margin = self.config.margin * inch
        y = height - margin

        # === HEADER SECTION ===
        y = self._render_header(c, label, margin, y, width)

        # === BARCODE SECTION ===
        y = self._render_barcode(c, label, margin, y, width)

        # === SHIP TO SECTION ===
        y = self._render_ship_to(c, label, margin, y, width)

        # === SHIP FROM SECTION ===
        y = self._render_ship_from(c, label, margin, y, width)

        # === CARTON INFO SECTION ===
        y = self._render_carton_info(c, label, margin, y, width)

        # === CONTENTS SECTION (if enabled) ===
        if self.config.show_contents and label.contents_summary:
            y = self._render_contents(c, label, margin, y, width)

    def _render_header(
        self,
        c: canvas.Canvas,
        label: ShippingLabel,
        margin: float,
        y: float,
        width: float
    ) -> float:
        """
        Render header section with shipment info.

        Returns:
            Updated y position
        """
        c.setFont("Helvetica-Bold", self.config.font_size_title)
        c.drawString(margin, y, "SHIPPING LABEL")

        # Carton sequence
        c.setFont("Helvetica", self.config.font_size_body)
        y -= 20
        c.drawString(
            margin,
            y,
            f"Carton {label.carton_sequence} of {label.total_cartons}"
        )

        # Shipment ID
        if label.shipment_id:
            y -= 15
            c.drawString(margin, y, f"Shipment: {label.shipment_id}")

        # Draw separator line
        y -= 10
        c.line(margin, y, width - margin, y)
        y -= 15

        return y

    def _render_barcode(
        self,
        c: canvas.Canvas,
        label: ShippingLabel,
        margin: float,
        y: float,
        width: float
    ) -> float:
        """
        Render SSCC barcode.

        Returns:
            Updated y position
        """
        try:
            # Generate barcode image
            barcode_img = self.barcode_gen.generate_sscc_barcode(
                sscc=label.sscc,
                format="PNG",
                height=self.config.barcode_height,
                width=0.3
            )

            if barcode_img:
                # Calculate barcode position (centered)
                barcode_width = 3.0 * inch  # Approximate width
                barcode_height = 0.8 * inch  # Approximate height
                x_centered = (width - barcode_width) / 2

                # Draw barcode
                img_reader = ImageReader(barcode_img)
                c.drawImage(
                    img_reader,
                    x_centered,
                    y - barcode_height,
                    width=barcode_width,
                    height=barcode_height,
                    preserveAspectRatio=True
                )

                y -= barcode_height + 10

                # Draw SSCC text if configured
                if self.config.include_human_readable:
                    c.setFont("Helvetica", self.config.font_size_small)
                    sscc_text = f"SSCC: {label.sscc.get_formatted_sscc()}"
                    text_width = c.stringWidth(sscc_text, "Helvetica", self.config.font_size_small)
                    c.drawString((width - text_width) / 2, y, sscc_text)
                    y -= 20

        except Exception as e:
            logger.warning(f"Could not render barcode: {e}")
            # Fallback: just show SSCC as text
            c.setFont("Helvetica-Bold", self.config.font_size_body)
            c.drawString(margin, y, f"SSCC: {label.sscc.get_full_sscc()}")
            y -= 25

        return y

    def _render_ship_to(
        self,
        c: canvas.Canvas,
        label: ShippingLabel,
        margin: float,
        y: float,
        width: float
    ) -> float:
        """
        Render ship-to address.

        Returns:
            Updated y position
        """
        c.setFont("Helvetica-Bold", self.config.font_size_body)
        c.drawString(margin, y, "SHIP TO:")
        y -= 15

        c.setFont("Helvetica", self.config.font_size_body)

        # Name
        c.drawString(margin, y, label.ship_to_name)
        y -= 12

        # Address
        c.drawString(margin, y, label.ship_to_address)
        y -= 12

        # City, State, ZIP
        location = f"{label.ship_to_city}, {label.ship_to_state} {label.ship_to_postal}"
        c.drawString(margin, y, location)
        y -= 20

        return y

    def _render_ship_from(
        self,
        c: canvas.Canvas,
        label: ShippingLabel,
        margin: float,
        y: float,
        width: float
    ) -> float:
        """
        Render ship-from address.

        Returns:
            Updated y position
        """
        c.setFont("Helvetica-Bold", self.config.font_size_small)
        c.drawString(margin, y, "SHIP FROM:")
        y -= 12

        c.setFont("Helvetica", self.config.font_size_small)

        # Name
        c.drawString(margin, y, label.ship_from_name)
        y -= 10

        # City, State (abbreviated)
        if label.ship_from_city and label.ship_from_state:
            location = f"{label.ship_from_city}, {label.ship_from_state}"
            c.drawString(margin, y, location)
            y -= 15

        return y

    def _render_carton_info(
        self,
        c: canvas.Canvas,
        label: ShippingLabel,
        margin: float,
        y: float,
        width: float
    ) -> float:
        """
        Render carton information (weight, items, etc.).

        Returns:
            Updated y position
        """
        c.setFont("Helvetica", self.config.font_size_small)

        # Weight
        if label.weight:
            c.drawString(margin, y, f"Weight: {label.weight:.2f} lbs")
            y -= 10

        # Item count
        if label.item_count:
            c.drawString(margin, y, f"Items: {label.item_count}")
            y -= 10

        # Carrier and service
        if label.carrier_name:
            carrier_text = label.carrier_name
            if label.service_level:
                carrier_text += f" - {label.service_level}"
            c.drawString(margin, y, carrier_text)
            y -= 10

        # Tracking number
        if label.tracking_number:
            c.drawString(margin, y, f"Tracking: {label.tracking_number}")
            y -= 10

        # PO number
        if label.purchase_order:
            c.drawString(margin, y, f"PO: {label.purchase_order}")
            y -= 15

        return y

    def _render_contents(
        self,
        c: canvas.Canvas,
        label: ShippingLabel,
        margin: float,
        y: float,
        width: float
    ) -> float:
        """
        Render carton contents list.

        Returns:
            Updated y position
        """
        if not label.contents_summary:
            return y

        c.setFont("Helvetica-Bold", self.config.font_size_small)
        c.drawString(margin, y, "CONTENTS:")
        y -= 10

        c.setFont("Helvetica", self.config.font_size_small - 1)

        # Show up to max_contents_lines
        for i, item_text in enumerate(label.contents_summary):
            if i >= self.config.max_contents_lines:
                c.drawString(margin, y, "...")
                y -= 8
                break

            c.drawString(margin, y, f"• {item_text}")
            y -= 8

        return y

    def _get_page_dimensions(self) -> tuple[float, float]:
        """
        Get page dimensions based on label size.

        Returns:
            Tuple of (width, height) in points
        """
        size_map = {
            LabelSize.LABEL_4X6: (4 * inch, 6 * inch),
            LabelSize.LABEL_4X8: (4 * inch, 8 * inch),
            LabelSize.LABEL_6X8: (6 * inch, 8 * inch),
            LabelSize.LETTER: (8.5 * inch, 11 * inch)
        }

        return size_map.get(self.config.label_size, (4 * inch, 6 * inch))

    def render_batch(
        self,
        labels: List[ShippingLabel],
        output_dir: str
    ) -> List[str]:
        """
        Render multiple labels to separate files.

        Args:
            labels: List of ShippingLabel objects
            output_dir: Directory to save label files

        Returns:
            List of output file paths
        """
        output_dir_path = Path(output_dir)
        output_dir_path.mkdir(parents=True, exist_ok=True)

        output_paths = []

        for i, label in enumerate(labels, 1):
            # Generate filename
            filename = f"label_carton_{label.carton_sequence}_{label.sscc.get_full_sscc()}.pdf"
            output_path = output_dir_path / filename

            # Render label
            self.render_label(label, str(output_path))
            output_paths.append(str(output_path))

            logger.info(f"Rendered label {i}/{len(labels)}")

        logger.info(f"Batch complete: {len(output_paths)} labels rendered")
        return output_paths


def create_label_renderer(config: Optional[LabelConfig] = None) -> LabelRenderer:
    """
    Convenience function to create a label renderer.

    Args:
        config: Label configuration (optional)

    Returns:
        LabelRenderer instance
    """
    return LabelRenderer(config)
