"""
ASN Builder Engine
==================
Main engine for building EDI 856 ASN documents from shipment data.

Converts ShipmentPackage → complete EDI 856 file.

Author: Integration Engineering Team
"""

from typing import List, Optional
from datetime import datetime
import logging

from src.models.internal_models import ShipmentPackage, Shipment
from src.models.asn_models import ASNDocument, ASNHeader, ASNSummary
from src.asn_builder.segments import SegmentGenerator
from src.asn_builder.hierarchy import HierarchyBuilder, HierarchyNode

logger = logging.getLogger(__name__)


class ASNBuilder:
    """
    Builds EDI 856 ASN documents from shipment packages.

    Usage:
        builder = ASNBuilder()
        edi_content = builder.build_asn(shipment_package)
        with open("856_output.txt", "w") as f:
            f.write(edi_content)
    """

    def __init__(
        self,
        segment_terminator: str = "~",
        element_separator: str = "*",
        subelement_separator: str = ":"
    ):
        """
        Initialize ASN builder.

        Args:
            segment_terminator: Segment terminator (default: ~)
            element_separator: Element separator (default: *)
            subelement_separator: Sub-element separator (default: :)
        """
        self.segment_terminator = segment_terminator
        self.element_separator = element_separator
        self.subelement_separator = subelement_separator

        self.seg_gen = SegmentGenerator(element_separator, subelement_separator)
        self.hierarchy_builder = HierarchyBuilder(self.seg_gen)

        logger.info("ASN Builder initialized")

    def build_asn(
        self,
        shipment_package: ShipmentPackage,
        sender_id: str = "SENDER",
        receiver_id: str = "RECEIVER",
        control_number: Optional[str] = None
    ) -> str:
        """
        Build complete EDI 856 ASN document.

        Args:
            shipment_package: ShipmentPackage with shipment data
            sender_id: EDI sender ID (ISA06/GS02)
            receiver_id: EDI receiver ID (ISA08/GS03)
            control_number: Control number (auto-generated if not provided)

        Returns:
            Complete EDI 856 document as string

        Raises:
            ValueError: If shipment package is invalid
        """
        logger.info(f"Building ASN for shipment {shipment_package.shipment.shipment_id}")

        # Validate input
        self._validate_shipment_package(shipment_package)

        # Generate control number if not provided
        if control_number is None:
            control_number = self._generate_control_number(shipment_package)

        shipment = shipment_package.shipment

        # Build all segments
        segments = []

        # === ENVELOPE HEADER ===

        # ISA segment
        segments.append(
            self.seg_gen.generate_isa(
                sender_id=sender_id,
                receiver_id=receiver_id,
                control_number=control_number,
                timestamp=shipment.ship_date
            )
        )

        # GS segment
        segments.append(
            self.seg_gen.generate_gs(
                sender_code=sender_id,
                receiver_code=receiver_id,
                control_number=control_number,
                timestamp=shipment.ship_date
            )
        )

        # === TRANSACTION SET ===

        # ST segment
        segments.append(
            self.seg_gen.generate_st(control_number)
        )

        # BSN segment
        segments.append(
            self.seg_gen.generate_bsn(
                shipment_id=shipment.shipment_id,
                ship_date=shipment.ship_date
            )
        )

        # === HIERARCHICAL LEVELS ===

        # Build HL hierarchy
        hierarchy_root = self.hierarchy_builder.build_hierarchy(shipment)

        # Get all segments from hierarchy (in proper depth-first order)
        hl_segments = hierarchy_root.get_all_segments()
        segments.extend(hl_segments)

        # === TRANSACTION SUMMARY ===

        # CTT segment (transaction totals)
        line_count = self.hierarchy_builder.get_line_item_count(hierarchy_root)
        segments.append(
            self.seg_gen.generate_ctt(
                line_count=line_count,
                total_weight=shipment.total_weight
            )
        )

        # === TRANSACTION SET TRAILER ===

        # SE segment (count includes ST and SE)
        transaction_segment_count = len(segments) - 2 + 2  # Subtract ISA/GS, add ST/SE
        segments.append(
            self.seg_gen.generate_se(
                segment_count=transaction_segment_count,
                control_number=control_number
            )
        )

        # === ENVELOPE TRAILER ===

        # GE segment (1 transaction set)
        segments.append(
            self.seg_gen.generate_ge(
                transaction_count=1,
                control_number=control_number
            )
        )

        # IEA segment (1 functional group)
        segments.append(
            self.seg_gen.generate_iea(
                group_count=1,
                control_number=control_number
            )
        )

        # === FORMAT OUTPUT ===

        # Join segments with terminators
        edi_content = self.segment_terminator.join(segments) + self.segment_terminator

        logger.info(
            f"ASN generation complete: {len(segments)} segments, "
            f"{line_count} line items"
        )

        return edi_content

    def build_asn_to_file(
        self,
        shipment_package: ShipmentPackage,
        output_path: str,
        sender_id: str = "SENDER",
        receiver_id: str = "RECEIVER",
        control_number: Optional[str] = None
    ) -> str:
        """
        Build ASN and write directly to file.

        Args:
            shipment_package: ShipmentPackage with shipment data
            output_path: Path to output file
            sender_id: EDI sender ID
            receiver_id: EDI receiver ID
            control_number: Control number

        Returns:
            Path to output file

        Raises:
            IOError: If file cannot be written
        """
        edi_content = self.build_asn(
            shipment_package,
            sender_id,
            receiver_id,
            control_number
        )

        with open(output_path, "w") as f:
            f.write(edi_content)

        logger.info(f"ASN written to file: {output_path}")
        return output_path

    def _validate_shipment_package(self, package: ShipmentPackage):
        """
        Validate shipment package before building ASN.

        Args:
            package: ShipmentPackage to validate

        Raises:
            ValueError: If package is invalid
        """
        if not package.shipment:
            raise ValueError("ShipmentPackage must have a shipment")

        shipment = package.shipment

        if not shipment.orders:
            raise ValueError("Shipment must have at least one order")

        if not shipment.cartons:
            raise ValueError("Shipment must have at least one carton")

        # Validate each carton has items
        for carton in shipment.cartons:
            if not carton.items:
                raise ValueError(f"Carton {carton.carton_id} must have at least one item")

            # Validate SSCC is present
            if not carton.sscc:
                raise ValueError(f"Carton {carton.carton_id} must have an SSCC")

    def _generate_control_number(self, package: ShipmentPackage) -> str:
        """
        Generate a control number based on shipment ID and timestamp.

        Args:
            package: ShipmentPackage

        Returns:
            Control number string
        """
        # Use timestamp-based control number
        timestamp = package.generated_at.strftime("%Y%m%d%H%M%S")
        # Take last 9 digits
        return timestamp[-9:]

    def count_segments(self, edi_content: str) -> int:
        """
        Count segments in EDI content.

        Args:
            edi_content: EDI document string

        Returns:
            Number of segments
        """
        return edi_content.count(self.segment_terminator)

    def format_for_display(self, edi_content: str, add_line_numbers: bool = True) -> str:
        """
        Format EDI content for human-readable display.

        Args:
            edi_content: EDI document string
            add_line_numbers: Whether to add line numbers

        Returns:
            Formatted string with one segment per line
        """
        segments = edi_content.split(self.segment_terminator)
        # Remove empty last segment
        if segments and not segments[-1]:
            segments = segments[:-1]

        if add_line_numbers:
            lines = []
            for i, segment in enumerate(segments, 1):
                lines.append(f"{i:3d}  {segment}")
            return "\n".join(lines)
        else:
            return "\n".join(segments)


def create_asn_builder(
    segment_terminator: str = "~",
    element_separator: str = "*",
    subelement_separator: str = ":"
) -> ASNBuilder:
    """
    Convenience function to create an ASN builder.

    Args:
        segment_terminator: Segment terminator
        element_separator: Element separator
        subelement_separator: Sub-element separator

    Returns:
        Configured ASNBuilder instance
    """
    return ASNBuilder(segment_terminator, element_separator, subelement_separator)
